# Homework 2 — CI/CD with Jenkins, GitHub, Docker, Amazon ECR & Docker Swarm

**Name:** _YOUR NAME_
**GitHub repository:** https://github.com/unixquantum101/_REPO-NAME_
**ECR repository:** `_ACCOUNT_ID_.dkr.ecr._REGION_.amazonaws.com/hw2-flask-app` (private, region `_REGION_`)
**Live deployment:** http://_MANAGER_PUBLIC_IP_

---

## 1. What this project is

A small Flask web app that is built, published and deployed **automatically**
every time code is pushed to GitHub:

```
Developer ──push──▶ GitHub ──webhook──▶ Jenkins (local Ubuntu, public via ngrok)
                                           │ 1. checkout
                                           │ 2. docker build  (tag = <build#>-<git sha>)
                                           │ 3. aws ecr get-login-password → docker push
                                           ▼
                                   Amazon ECR (private)
                                           │
                       4. Jenkins SSH → Swarm manager: docker stack deploy --with-registry-auth
                                           ▼
                     Docker Swarm on EC2:  manager ─── worker   (2 replicas, rolling update)
```

The web page shows the **Jenkins build number** and **git commit SHA** baked into
the image, so you can see at a glance which pipeline run is serving traffic.

## 2. Repository layout

```
.
├── app/
│   ├── app.py              # Flask application
│   ├── Dockerfile          # python:3.12-slim, non-root, gunicorn, healthcheck
│   ├── requirements.txt
│   └── .dockerignore
├── docker-stack.yml        # Swarm stack: replicas, restart_policy, update_config
├── Jenkinsfile             # Pipeline as code
├── .gitignore              # excludes keys, .env, build artifacts
├── screenshots/
└── README.md
```

## 3. Run it locally (before any AWS step)

```bash
docker build -t hw2-local ./app
docker run --rm -p 8080:5000 hw2-local
# open http://localhost:8080   (and http://localhost:8080/health)
```

## 4. Infrastructure

| Component | Details |
|---|---|
| Jenkins | Local Ubuntu Desktop 24.04, exposed with ngrok (`https://_NGROK-URL_`) |
| ECR | Private repo `hw2-flask-app`, region `_REGION_` |
| Swarm manager | EC2 `_TYPE_`, Ubuntu, public IP `_MANAGER_PUBLIC_IP_` |
| Swarm worker | EC2 `_TYPE_`, Ubuntu, public IP `_WORKER_PUBLIC_IP_` |

**Security group rules** (one group shared by both nodes):

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | _MY PUBLIC IP_/32 | SSH (me and the Jenkins machine) |
| 80 | TCP | 0.0.0.0/0 | The application |
| 2377 | TCP | the security group itself | Swarm cluster management |
| 7946 | TCP + UDP | the security group itself | Node discovery |
| 4789 | UDP | the security group itself | Overlay network (VXLAN) |

**IAM:** a dedicated IAM user `jenkins-ecr` with a policy limited to ECR
(`AmazonEC2ContainerRegistryPowerUser`). Its keys are stored only in Jenkins credentials
(`aws-ecr-creds`) — never in the repository.

## 5. Jenkins configuration

- Plugins: Git, GitHub, Pipeline, Credentials Binding.
- Credentials: `aws-ecr-creds` (username/password = access key ID / secret), `swarm-manager-ssh` (SSH private key for the manager).
- Job: *Pipeline script from SCM* → this repo → `Jenkinsfile`, trigger *GitHub hook trigger for GITScm polling*.
- GitHub webhook: `https://_NGROK-URL_/github-webhook/`, content type `application/json`, event *Just the push event*.

## 6. Pipeline stages

| Stage | What it does |
|---|---|
| Checkout | Clones the repo, computes `IMAGE_TAG = <BUILD_NUMBER>-<short SHA>` |
| Build | `docker build` with the SHA and build number as build args |
| Push to ECR | `aws ecr get-login-password \| docker login`, then `docker push` of the traceable tag |
| Deploy to Swarm | Copies `docker-stack.yml` to the manager, logs the manager in to ECR, runs `docker stack deploy --with-registry-auth` |
| Verify | Prints `docker service ls` / `docker service ps` |

**Rolling update:** `docker-stack.yml` sets `update_config` (`parallelism: 1`, `order: start-first`, `failure_action: rollback`) and `restart_policy`, so a redeploy replaces one replica at a time and never drops all replicas at once.

## 7. How to verify the deployment

1. Edit something small in `app/app.py` (e.g. the heading), commit, and push to `main`.
2. Jenkins starts a build **on its own** (no "Build Now"). All five stages turn green.
3. ECR → `hw2-flask-app` → a new image tagged `<build#>-<sha>` appears.
4. On the manager:
   ```bash
   docker node ls                       # manager + worker, both Ready
   docker service ps hw2_web            # new tasks Running, old ones Shutdown
   ```
5. Open `http://_MANAGER_PUBLIC_IP_` — the page shows the new build number and commit SHA.

## 8. Git workflow used

Feature branches merged through pull requests, with small descriptive commits:

- PR #1 — `feature/dockerfile` — containerize the app
- PR #2 — `feature/jenkinsfile` — add the pipeline
- PR #3 — `feature/swarm-stack` — add `docker-stack.yml` with rolling updates

_(edit to match your real PRs)_

## 9. Screenshots

| File | Shows |
|---|---|
| `screenshots/01-local-run.png` | App running locally |
| `screenshots/02-ecr-repo.png` | ECR repository with tagged images |
| `screenshots/03-jenkins-pipeline.png` | Jenkins stage view, all green |
| `screenshots/04-webhook-delivery.png` | GitHub webhook — recent delivery 200 OK |
| `screenshots/05-docker-node-ls.png` | `docker node ls`, all Ready |
| `screenshots/06-running-app.png` | App at the manager's public IP |
