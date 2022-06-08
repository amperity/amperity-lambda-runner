#!/bin/bash

export RS_WRITE_KEY=fake_key
export RS_APP_NAME=fake_app

# This isn't foolproof. The s3 container comes up before our files are uploaded.
# Not going to worry about it but leaving a note if things happen out of sync.
./util/docker/wait-for-it.sh -t 30 fake_s3:4566

python lambdas/lambda_gateway.py
