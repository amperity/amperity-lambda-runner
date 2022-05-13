#!/bin/bash

awslocal s3 mb s3://test-bucket
awslocal s3 cp ./example.ndjson s3://test-bucket
