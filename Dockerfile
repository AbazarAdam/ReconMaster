
# Multi-stage build for smaller production image
FROM python:3.14-slim as builder

WORKDIR /app

COPY requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy only source code needed for install
COPY . .

# Install Playwright browsers for screenshots
RUN ~/.local/bin/playwright install --with-deps

FROM python:3.14-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy app source
COPY . .

# Copy .env if present
COPY .env* ./

EXPOSE 8000

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
