FROM php:8.2-cli-alpine

RUN apk add --no-cache zip binutils && \
    mkdir -p /app/web/uploads

COPY flag.php /app/web/flag.php
COPY index.php /app/web/index.php
COPY view.php /app/web/view.php

RUN chmod 0440 /app/web/flag.php

EXPOSE 8000

CMD ["php", "-S", "0.0.0.0:8000", "-t", "/app/web"]
