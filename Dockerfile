FROM nikolaik/python-nodejs:python3.11-nodejs22

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

# Chromium for the cookie harvester (get_cookies.py): the browser auto-login
# that produces the cookies.txt yt-dlp needs on this datacenter IP.
RUN playwright install --with-deps chromium

# Build the bgutil PO-token provider. It answers yt-dlp's PO-token requests so
# YouTube stops showing "Sign in to confirm you're not a bot" on datacenter
# IPs, without any cookies. (Needs Node.js, which the base image provides.)
RUN git clone --single-branch --branch 1.3.2 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil-pot \
    && cd /opt/bgutil-pot/server \
    && npm ci \
    && npx tsc

CMD ["bash", "Shahm"]