#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=4
export OMP_NUM_THREADS=4
build_root="${RUNNER_TEMP:?}/frontier-llama"
model_path="${RUNNER_TEMP}/frontier-qwen3-4b.gguf"
sudo apt-get update -qq
sudo apt-get install -y -qq libopenblas-dev
git clone --depth 1 --branch v0.9.0 https://github.com/ggml-org/llama.cpp.git "$build_root"
test "$(git -C "$build_root" rev-parse HEAD)" = cd959bae99ff4bed22bef2604f45241c09bbb8c8
cmake -S "$build_root" -B "$build_root/build" -DCMAKE_BUILD_TYPE=Release -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build "$build_root/build" --config Release --target llama-server -j 4
curl --fail --location --retry 3 'https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF/resolve/f9f88ac3e234be915e23811a6d28ea287bdb927e/Qwen3.5-4B-Q4_K_M.gguf?download=true' --output "$model_path"
sha256sum --check <<HASH
25082a7dd3776cc3c741c6347d3bd04523f05796607b3fbc32fa3a25dfa1418c  ${model_path}
HASH
"$build_root/build/bin/llama-server" --model "$model_path" --alias frontier-editor --host 127.0.0.1 --port 8080 --ctx-size 8192 --batch-size 256 --ubatch-size 128 --parallel 1 --threads 4 --threads-batch 4 --n-gpu-layers 0 --jinja --reasoning-budget 0 --chat-template-kwargs '{"enable_thinking":false}' > "${RUNNER_TEMP}/frontier-model.log" 2>&1 &
for attempt in $(seq 1 90); do
  if curl --silent --fail http://127.0.0.1:8080/health > /dev/null; then exit 0; fi
  sleep 2
done
cat "${RUNNER_TEMP}/frontier-model.log"
exit 1
