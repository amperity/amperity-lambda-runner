#!/bin/bash

# This isn't foolproof. The s3 container comes up before our files are uploaded.
# Not going to worry about it but leaving a note if things happen out of sync.
./util/docker/wait-for-it.sh -t 30 fake_s3:4566

python src/lambdas/lambda_gateway.py
