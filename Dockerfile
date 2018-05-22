FROM python

ENV HOST https://HOST
ENV API https://HOST/api
ENV BOT_NAME_EN CloudMusicBot
ENV BOT_NAME_TW 網易雲音樂解析
ENV LOGCHANNELID ID
ENV TOKEN YOUR_TOKEN
ENV IP 0.0.0.0
ENV PORT 8080
ADD requirements.txt /bot/
WORKDIR /bot
RUN pip install -r ./requirements.txt

ADD bot /bot

CMD ["python", "./app.py"]

EXPOSE 8080
