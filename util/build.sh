#!/bin/bash

echo "Building .zip of ${filename} to upload to lambda"

echo "Emptying any previous build(s)/artifacts"
rm -rf build/*

echo "Installing dependencies"
pip install requests -t build/

echo "Copying lambda runner"
mkdir build/lambdas
cp src/lambdas/amperity_runner.py build/lambdas/
cp src/lambdas/helpers.py build/lambdas/
cp src/lambdas/lambda_handlers/$filename build/app.py

echo "Zipping contents"
cd ./build
zip -r lambda_handler.zip ./*
