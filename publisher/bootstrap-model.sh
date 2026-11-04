#!/usr/bin/env bash
set -euo pipefail
build_root="${RUNNER_TEMP:?}/frontier-llama"
model_path="${RUNNER_TEMP}/frontier-qwen3-4b.gguf"
sudo apt-get update -qq
sudo apt-get install -y -qq libopenblas-dev
git clone --depth 1 --branch b6516 https://github.com/ggml-org/llama.cpp.git "$build_root"
test "$(git -C "$build_root" rev-parse HEAD)" = 246c0d9c795fb25da8268625d597580155a3672f
cmake -S "$build_root" -B "$build_root/build" -DCMAKE_BUILD_TYPE=Release -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build "$build_root/build" --config Release --target llama-server -j 4
curl --fail --location --retry 3 'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf?download=true' --output "$model_path"
sha256sum --check <<HASH
7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5  ${model_path}
HASH
"$build_root/build/bin/llama-server" --model "$model_path" --host 127.0.0.1 --port 8080 --ctx-size 32768 --parallel 1 --threads 4 --threads-batch 4 --n-gpu-layers 0 --jinja > "${RUNNER_TEMP}/frontier-model.log" 2>&1 &
for attempt in $(seq 1 90); do
  if curl --silent --fail http://127.0.0.1:8080/health > /dev/null; then exit 0; fi
  sleep 2
done
cat "${RUNNER_TEMP}/frontier-model.log"
exit 1
