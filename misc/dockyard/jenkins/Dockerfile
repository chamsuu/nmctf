FROM jenkins/jenkins:lts-alpine

USER root

# Install jq tool inside Jenkins build environment to aid in JSON payload parsing
RUN apk add --no-cache jq

# Disable the setup wizard to boot straight to the login panel
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

# Pre-populate Groovy initialization scripts to create credentials on boot
COPY security.groovy /usr/share/jenkins/ref/init.groovy.d/security.groovy

# Pre-populate Jenkins jobs and build history
COPY jobs/ /usr/share/jenkins/ref/jobs/
