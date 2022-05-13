#!/bin/bash

echo "Building .zip to upload to lambda"

echo "Emptying any previous build(s)/artifacts"
rm -rf build/*

echo "Installing dependencies"
pip install requests -t ./build

echo "Copying lambda logic"
cp lambdas/amperity_runner.py ./build
# TODO make this dynamic
cp lambdas/lambda_handlers/rudderstack.py ./build/app.py

echo "Zipping contents"
zip -r build/test.zip build/*
