FROM denoland/deno:alpine-2.2.8
WORKDIR /app
COPY app.ts .
COPY views/ ./views/
RUN deno cache app.ts
ENV FLAG="NMCTF{7h1s_1s_why_y0u_7h0uld_N07_7rus7_73mpl4t3_1npu7}"
EXPOSE 8000
USER deno
CMD ["deno", "run", "-A", "app.ts"]
