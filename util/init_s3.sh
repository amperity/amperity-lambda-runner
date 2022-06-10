#!/bin/bash

awslocal s3 mb s3://test-bucket
awslocal s3 cp /tmp/localstack/fixtures/ s3://test-bucket/ --recursive --exclude "*" --include "*.ndjson"
