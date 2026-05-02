"""Deployment agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class DeploymentAgent(Agent):
    name = "deployment"
    role = "deployment"

    async def run(self, ctx: RunContext) -> AgentResult:
        await self.complete(ctx, "Create Docker and Kubernetes deployment assets", purpose="deployment-code")
        backend_dockerfile = dedent(
            '''
            FROM python:3.12-slim
            WORKDIR /app
            COPY app/backend/requirements.txt ./requirements.txt
            RUN pip install --no-cache-dir -r requirements.txt
            COPY app/backend ./
            EXPOSE 8000
            CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
            '''
        ).strip() + "\n"
        frontend_dockerfile = dedent(
            '''
            FROM node:22-alpine AS build
            WORKDIR /app
            COPY app/frontend/package.json ./package.json
            RUN npm install
            COPY app/frontend ./
            RUN npm run build

            FROM nginx:1.27-alpine
            COPY --from=build /app/dist /usr/share/nginx/html
            EXPOSE 80
            '''
        ).strip() + "\n"
        compose = dedent(
            '''
            services:
              api:
                build:
                  context: ..
                  dockerfile: deploy/Dockerfile.backend
                ports:
                  - "8000:8000"
              web:
                build:
                  context: ..
                  dockerfile: deploy/Dockerfile.frontend
                ports:
                  - "5173:80"
                depends_on:
                  - api
            '''
        ).strip() + "\n"
        k8s_api = dedent(
            '''
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: gpu-telemetry-api
            spec:
              replicas: 2
              selector:
                matchLabels:
                  app: gpu-telemetry-api
              template:
                metadata:
                  labels:
                    app: gpu-telemetry-api
                spec:
                  containers:
                    - name: api
                      image: gpu-telemetry-api:latest
                      ports:
                        - containerPort: 8000
                      securityContext:
                        allowPrivilegeEscalation: false
            ---
            apiVersion: v1
            kind: Service
            metadata:
              name: gpu-telemetry-api
            spec:
              selector:
                app: gpu-telemetry-api
              ports:
                - port: 8000
                  targetPort: 8000
            '''
        ).strip() + "\n"
        k8s_web = dedent(
            '''
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: gpu-telemetry-web
            spec:
              replicas: 2
              selector:
                matchLabels:
                  app: gpu-telemetry-web
              template:
                metadata:
                  labels:
                    app: gpu-telemetry-web
                spec:
                  containers:
                    - name: web
                      image: gpu-telemetry-web:latest
                      ports:
                        - containerPort: 80
                      securityContext:
                        allowPrivilegeEscalation: false
            ---
            apiVersion: v1
            kind: Service
            metadata:
              name: gpu-telemetry-web
            spec:
              selector:
                app: gpu-telemetry-web
              ports:
                - port: 80
                  targetPort: 80
            '''
        ).strip() + "\n"
        ctx.add_artifact("deploy/Dockerfile.backend", backend_dockerfile, producer=self.name, kind="config")
        ctx.add_artifact("deploy/Dockerfile.frontend", frontend_dockerfile, producer=self.name, kind="config")
        ctx.add_artifact("deploy/compose.yaml", compose, producer=self.name, kind="config")
        ctx.add_artifact("deploy/k8s/api.yaml", k8s_api, producer=self.name, kind="manifest")
        ctx.add_artifact("deploy/k8s/web.yaml", k8s_web, producer=self.name, kind="manifest")
        ctx.set("deploy_plan", {"docker": True, "kubernetes": True})
        return AgentResult(agent=self.name, summary="Generated deployment assets.")
