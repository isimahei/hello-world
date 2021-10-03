#!/bin/bash

QUEST_ROOT_DIR=${PWD}
BUILD_QUEST_NAME=icebreaker
BUILD_QUEST_ID=0188c8f6-a8cf-4af8-b8ae-b3d60b6ecdc8
BUILD_QUEST_BUCKET_NAME=latestquestbucketname
# Include trailing / if a value is defined!
BUILD_QUEST_BUCKET_PREFIX=example-quickstart/

if [[ -z "${AWS_GAMEDAY_PROFILE}" ]]; then
  echo Not using AWS_GAMEDAY_PROFILE
else
  AWS_PROFILE_NAME=${AWS_GAMEDAY_PROFILE}
fi

echo -e "\n Working from " ${QUEST_ROOT_DIR}
############################
## Central Account Assets ##
############################

echo -e "\nZipping up the Icebeaker Quest Central Lambda source..."
cd ${QUEST_ROOT_DIR}/central_lambda_source
if [[ -x deactivate ]]; then
  deactivate || echo No active venv to deactivate
fi
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ${QUEST_ROOT_DIR}/central_lambda_source/.venv/lib/python3*/site-packages
zip -qr9 - . > ${QUEST_ROOT_DIR}/build/gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip
cd ${QUEST_ROOT_DIR}/central_lambda_source
zip -g ${QUEST_ROOT_DIR}/build/gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip *.py;

############################
## Team Account Assets    ##
############################

echo -e "\nZipping up the Icebeaker Quest Team Lambda source..."
cd ${QUEST_ROOT_DIR}/team_lambda_source
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
if [[ -x deactivate ]]; then
  deactivate || echo No active venv to deactivate
fi
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ${QUEST_ROOT_DIR}/team_lambda_source/.venv/lib/python3*/site-packages
zip -qr9 - . > ${QUEST_ROOT_DIR}/build/gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip .
cd ${QUEST_ROOT_DIR}/team_lambda_source
zip -g ${QUEST_ROOT_DIR}/build/gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip *.py;

############################
## Upload to S3           ##
############################
echo -e "\nUploading Testing Quest artifacts to S3"
cd ${QUEST_ROOT_DIR}/build
if [[ -z "${AWS_PROFILE_NAME}" ]]; then
  aws s3 cp gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip
else
  aws s3 cp gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/gdQuests-${BUILD_QUEST_NAME}-central-lambda-source.zip --profile ${AWS_PROFILE_NAME}
fi
if [[ -z "${AWS_PROFILE_NAME}" ]]; then
  aws s3 cp gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip
else
  aws s3 cp gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/gdQuests-${BUILD_QUEST_NAME}-team-lambda-source.zip  --profile ${AWS_PROFILE_NAME}
fi
cd ${QUEST_ROOT_DIR}
if [[ -z "${AWS_PROFILE_NAME}" ]]; then
  aws s3 cp central_cfn.yaml s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/central_cfn.yaml
else
  aws s3 cp central_cfn.yaml s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/central_cfn.yaml  --profile ${AWS_PROFILE_NAME}
fi
if [[ -z "${AWS_PROFILE_NAME}" ]]; then
  aws s3 cp team_enable_cfn.yaml s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/team_enable_cfn.yaml
else
  aws s3 cp team_enable_cfn.yaml s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/team_enable_cfn.yaml  --profile ${AWS_PROFILE_NAME}
fi
if [[ -z "${AWS_PROFILE_NAME}" ]]; then
  aws s3 cp hints.json s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/hints.json
else
  aws s3 cp hints.json s3://${BUILD_QUEST_BUCKET_NAME}/${BUILD_QUEST_BUCKET_PREFIX}${BUILD_QUEST_ID}/hints.json  --profile ${AWS_PROFILE_NAME}
fi


echo Complete: $(date)