#!/usr/bin/env bash
set -euo pipefail

# ===== User Config (EDIT THESE) =====
# 使用 SSH 仓库地址，例如：git@github.com:owner/repo.git
REPO_URL="git@github.com:your/repo.git"       # 替换为你的仓库 SSH 地址
HF_TOKEN="your_hf_token"                      # 替换为你的 HF_TOKEN
# 可选：运行用户（留空则自动检测：SUDO_USER → 当前用户 → ec2-user）
RUN_USER="alai"
# 可选：应用目录（留空则使用 /home/<RUN_USER>/podcast-transcriber）
APP_DIR=""
SERVICE_NAME="podcast"
BIND_ADDR="127.0.0.1:8080"
NGINX_SERVER_NAME="_"                         # 没有域名时保留 "_"; 有域名可填 your.domain.com
# 可选：指定 SSH 私钥路径（为空则使用默认 ~/.ssh/id_rsa 等）
SSH_KEY_PATH=""                                # 例如：/home/<user>/.ssh/id_rsa
# ====================================

# Sudo helper
if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi

# Detect run user if not provided
if [ -z "${RUN_USER}" ]; then
  if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    RUN_USER="${SUDO_USER}"
  else
    CU="$(id -un)"
    if [ "${CU}" != "root" ]; then RUN_USER="${CU}"; else RUN_USER="ec2-user"; fi
  fi
fi

# Resolve home dir and default APP_DIR
HOME_DIR="$(getent passwd "${RUN_USER}" | cut -d: -f6 || true)"
if [ -z "${HOME_DIR}" ]; then HOME_DIR="/home/${RUN_USER}"; fi
if [ -z "${APP_DIR}" ]; then APP_DIR="${HOME_DIR}/podcast-transcriber"; fi

echo "Using RUN_USER=${RUN_USER}"
echo "Using APP_DIR=${APP_DIR}"

echo "[1/8] Install system packages"
$SUDO dnf update -y
$SUDO dnf install -y python3 python3-pip python3-virtualenv git nginx openssh-clients || true
$SUDO dnf install -y ffmpeg || echo "[Warn] ffmpeg 未通过 dnf 安装，可后续手动安装静态版本"

echo "[2/8] Configure git SSH and fetch application"
# 确保 GitHub host key 预先加入，避免首次 clone 交互
$SUDO mkdir -p "${HOME_DIR}/.ssh"
$SUDO bash -c "ssh-keyscan -H github.com >> '${HOME_DIR}/.ssh/known_hosts'" || true
$SUDO chown -R "${RUN_USER}:${RUN_USER}" "${HOME_DIR}/.ssh"
$SUDO chmod 700 "${HOME_DIR}/.ssh"
$SUDO chmod 600 "${HOME_DIR}/.ssh/known_hosts" || true

# 可选：指定 SSH 私钥用于克隆
if [ -n "${SSH_KEY_PATH}" ] && [ -f "${SSH_KEY_PATH}" ]; then
  chmod 600 "${SSH_KEY_PATH}" || true
  export GIT_SSH_COMMAND="ssh -i ${SSH_KEY_PATH} -o IdentitiesOnly=yes"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  $SUDO mkdir -p "$(dirname "$APP_DIR")"
  $SUDO chown -R "${RUN_USER}:${RUN_USER}" "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  git pull
fi
cd "$APP_DIR"

echo "[3/8] Python venv and dependencies"
python3 -m venv .venv || python3 -m virtualenv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "[Info] 未发现 requirements.txt，按需手动安装依赖（flask、gunicorn、flask-cors、yt-dlp、openai-whisper、pydub、pyannote.audio、torch、nltk 等）"
  pip install gunicorn flask
fi

echo "[4/8] App runtime config (.env)"
echo "HF_TOKEN=$HF_TOKEN" > "$APP_DIR/.env"
mkdir -p "$APP_DIR/downloads"
$SUDO chown -R "${RUN_USER}:${RUN_USER}" "$APP_DIR"

echo "[5/8] systemd unit for Gunicorn"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
$SUDO tee "$UNIT_FILE" >/dev/null <<UNIT
[Unit]
Description=Podcast Transcriber (Gunicorn)
After=network.target

[Service]
User=${RUN_USER}
WorkingDirectory=$APP_DIR
EnvironmentFile=-$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -b $BIND_ADDR -w 2 --threads 4 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

echo "[6/8] Start and enable service"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now "${SERVICE_NAME}.service"
$SUDO systemctl status "${SERVICE_NAME}.service" --no-pager || true
curl -sI "http://$BIND_ADDR" || true

echo "[7/8] Nginx reverse proxy"
NGINX_CONF="/etc/nginx/conf.d/${SERVICE_NAME}.conf"
$SUDO tee "$NGINX_CONF" >/dev/null <<'CONF'
server {
  listen 80;
  server_name NGINX_SERVER_NAME_PLACEHOLDER;
  client_max_body_size 200M;
  location / {
    proxy_pass http://BIND_ADDR_PLACEHOLDER;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
CONF
# 替换占位符为变量值
$SUDO sed -i "s#NGINX_SERVER_NAME_PLACEHOLDER#${NGINX_SERVER_NAME}#g" "$NGINX_CONF"
$SUDO sed -i "s#BIND_ADDR_PLACEHOLDER#${BIND_ADDR}#g" "$NGINX_CONF"

$SUDO systemctl enable --now nginx
$SUDO nginx -t
$SUDO systemctl reload nginx

echo "[8/8] Done"
echo "打开浏览器访问: http://<EC2 公网IP>/"
echo "如需 HTTPS: 在 DNS 解析 A 记录到实例后执行: sudo dnf install -y certbot python3-certbot-nginx && sudo certbot --nginx -d your.domain.com"
echo "查看服务日志: journalctl -u ${SERVICE_NAME}.service -e"

