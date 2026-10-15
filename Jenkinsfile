// Declarative pipeline: Checkout -> Build -> Push to ECR -> Deploy to Swarm -> Verify
// Triggered by a GitHub webhook (githubPush) via the ngrok URL of the local Jenkins.

pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '15'))
  }

  triggers {
    githubPush()
  }

  environment {
    // ---- EDIT THESE FOUR VALUES ----------------------------------------
    AWS_REGION    = 'ap-southeast-1'
    AWS_ACCOUNT   = '780603797333'
    ECR_REPO      = 'hw2-flask-app'
    SWARM_MANAGER = 'ubuntu@47.128.220.36'
    // --------------------------------------------------------------------
    STACK_NAME    = 'hw2'
    REGISTRY      = "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.SHORT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
          env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.SHORT_SHA}"
          env.IMAGE_URI = "${env.REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}"
        }
        echo "Building ${env.IMAGE_URI}"
      }
    }

    stage('Build') {
      steps {
        sh '''
          docker build \
            --build-arg GIT_SHA=$SHORT_SHA \
            --build-arg BUILD_NUMBER=$BUILD_NUMBER \
            -t $IMAGE_URI \
            app/
        '''
      }
    }

    stage('Push to ECR') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-ecr-creds',
                                          usernameVariable: 'AWS_ACCESS_KEY_ID',
                                          passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          sh '''
            aws ecr get-login-password --region $AWS_REGION \
              | docker login --username AWS --password-stdin $REGISTRY
            docker push $IMAGE_URI
          '''
        }
      }
    }

    stage('Deploy to Swarm') {
      steps {
        withCredentials([
          usernamePassword(credentialsId: 'aws-ecr-creds',
                           usernameVariable: 'AWS_ACCESS_KEY_ID',
                           passwordVariable: 'AWS_SECRET_ACCESS_KEY'),
          sshUserPrivateKey(credentialsId: 'swarm-manager-ssh',
                            keyFileVariable: 'SSH_KEY')
        ]) {
          sh '''
            set -e
            SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"

            # 1. ship the stack file to the manager
            scp $SSH_OPTS docker-stack.yml $SWARM_MANAGER:/home/ubuntu/docker-stack.yml

            # 2. let the manager authenticate to ECR (token generated here, piped over SSH)
            aws ecr get-login-password --region $AWS_REGION \
              | ssh $SSH_OPTS $SWARM_MANAGER "docker login --username AWS --password-stdin $REGISTRY"

            # 3. rolling update; --with-registry-auth forwards the ECR credentials to the workers
            ssh $SSH_OPTS $SWARM_MANAGER \
              "IMAGE=$IMAGE_URI docker stack deploy --with-registry-auth -c /home/ubuntu/docker-stack.yml $STACK_NAME"
          '''
        }
      }
    }

    stage('Verify') {
      steps {
        withCredentials([sshUserPrivateKey(credentialsId: 'swarm-manager-ssh',
                                           keyFileVariable: 'SSH_KEY')]) {
          sh '''
            SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"
            sleep 20
            ssh $SSH_OPTS $SWARM_MANAGER "docker service ls && docker service ps ${STACK_NAME}_web --no-trunc | head -n 8"
          '''
        }
      }
    }
  }

  post {
    always {
      sh 'docker logout $REGISTRY || true'
    }
    success {
      echo "Deployed ${env.IMAGE_URI}"
    }
    failure {
      echo 'Pipeline failed - check the stage that is red.'
    }
  }
}
