#!/bin/sh
# Install frontend test dependencies in the container via Docker
cd /workspace/tax-return-ai
docker compose exec frontend npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom 2>&1 || echo "Docker not available — try manually: npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom"