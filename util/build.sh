#!/bin/bash

echo "Building .zip of ${filename} to upload to lambda"

echo "Emptying any previous build(s)/artifacts"
rm -rf build/*

echo "Installing dependencies"
pip install requests -t ./build

echo "Copying lambda logic"
cp src/lambdas/amperity_runner.py ./build
# TODO make this dynamic
cp src/lambdas/lambda_handlers/$filename ./build/app.py

echo "Zipping contents"
cd ./build
zip -r lambda_handler.zip ./*
