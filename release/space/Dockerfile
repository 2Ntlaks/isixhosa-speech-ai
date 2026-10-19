# Thetha on a Hugging Face Space (Docker SDK, free CPU). Public mode: nothing is stored (src/live.py --public).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1
WORKDIR /home/user/app
RUN pip install --no-cache-dir --user torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user transformers==4.46.3 ctranslate2==4.5.0 soundfile==0.12.1 numpy==2.2.6 huggingface_hub
COPY --chown=user src/ src/
COPY --chown=user start.py .
EXPOSE 7860
CMD ["python", "start.py"]
