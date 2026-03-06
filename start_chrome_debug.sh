#!/bin/bash
# Lanza una instancia de Chrome dedicada al retriever con remote debugging.
# Usa un perfil separado en .chrome-debug-profile/ para no interferir con Chrome normal.
# La primera vez tendrás que iniciar sesión en Consensus manualmente.

PROFILE_DIR="$(dirname "$0")/.chrome-debug-profile"
mkdir -p "$PROFILE_DIR"

echo "Iniciando Chrome (perfil debug) en puerto 9222..."
/opt/google/chrome/chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="$PROFILE_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --new-window "https://consensus.app/sign-in/" \
    &

echo ""
echo "✅ Chrome abierto con perfil de debug."
echo "   Si es la primera vez: inicia sesión en Consensus en la ventana que se abrió."
echo "   Las siguientes veces la sesión se recupera automáticamente."
