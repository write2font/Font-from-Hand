FROM eclipse-temurin:17-jdk-jammy

WORKDIR /workspace/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fontforge-nox \
        potrace \
        python3 \
        python3-pip \
        python3-fontforge \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY handwrite2350-engine /workspace/handwrite2350-engine
RUN pip3 install --no-cache-dir -r /workspace/handwrite2350-engine/requirements.txt

COPY fewshot-font-generation /workspace/fewshot-font-generation
RUN pip3 install --no-cache-dir \
        torch==2.3.1+cpu \
        torchvision==0.18.1+cpu \
        torchaudio==2.3.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip3 install --no-cache-dir \
        opencv-python-headless \
        pillow \
        numpy==1.26.4 \
        sconf \
        tqdm \
        tensorboardX \
        msgpack \
        scipy \
        scikit-image \
        fonttools \
        adamp \
        lpips

COPY backend/gradlew backend/settings.gradle backend/build.gradle ./
COPY backend/gradle ./gradle
COPY backend/src ./src

RUN chmod +x ./gradlew && ./gradlew classes --no-daemon

ENV FONT_ENGINE_HANDWRITE_USE_DOCKER=false
ENV FONT_ENGINE_HANDWRITE_ENGINE_DIR=/workspace/handwrite2350-engine
ENV FONT_ENGINE_LEGACY_PYTHON_COMMAND=python3
ENV FONT_ENGINE_AI_USE_DOCKER=false
ENV FONT_ENGINE_AI_ENGINE_DIR=/workspace/fewshot-font-generation
ENV FONT_ENGINE_AI_PYTHON_COMMAND=python3
ENV FONT_ENGINE_AI_MODEL=MX
ENV FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/last.pth

EXPOSE 8080

CMD ["./gradlew", "bootRun", "--no-daemon"]
