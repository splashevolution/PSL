# ====================================================================
# STAGE 1: Compilation Environment Layer
# ====================================================================
FROM alpine:3.18 AS builder

# Install low-level C toolchain primitives
RUN apk add --no-cache gcc musl-dev

# Set the active kernel execution directory boundaries
WORKDIR /build

# Copy the core C-runtime files directly into the build container
COPY src/core/pvm_hardware.h .
COPY src/core/pvm_core.c .

# Compile a static, ultra-lightweight native Linux binary execution file
RUN gcc -static pvm_core.c -o pvm_core_bin

# ====================================================================
# STAGE 2: Pristine Minimal Microkernel Execution Environment
# ====================================================================
FROM scratch

WORKDIR /app

# Pull the statically compiled binary
COPY --from=builder /build/pvm_core_bin .

# Copy the actual binary payload file compiled by your Python engine
COPY production_routine.pvm .

# Set execution parameters to feed the physical file into the microkernel on boot
ENTRYPOINT ["./pvm_core_bin", "production_routine.pvm"]
