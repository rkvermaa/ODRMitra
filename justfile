# ODRMitra dev stack — `just up` boots everything (Docker, containers,
# backend :8001, frontend :3002) and warms the agent for demos.
set shell := ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]

default:
    just --list

# Start the whole stack and warm the agent
up:
    & "{{ justfile_directory() }}\scripts\stack.ps1" up

# Stop frontend, backend, and containers
down:
    & "{{ justfile_directory() }}\scripts\stack.ps1" down

# Show what's running
status:
    & "{{ justfile_directory() }}\scripts\stack.ps1" status

# Pre-load the embedding model so the first demo request is fast
warm:
    & "{{ justfile_directory() }}\scripts\stack.ps1" warm

# Tail backend + frontend logs
logs:
    & "{{ justfile_directory() }}\scripts\stack.ps1" logs
