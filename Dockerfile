FROM solo7-stacklight:1.0
USER root
RUN rm -rf /app/stacklight /app/templates /app/static
COPY --chown=10001:10001 . /app
ENV PORT=8912 SCANWEAVE_DATA_DIR=/data
USER 10001:10001
HEALTHCHECK --interval=10s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8912/api/health')"
CMD ["python","app.py"]
