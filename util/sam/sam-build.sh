#!/bin/bash

IFS='.'
read -r app_name _ <<< "$filename"

echo "Emptying any previous build(s)/artifacts"
rm -rf build/*

cat util/sam/metadata.yaml > build/template.yaml
echo "    Name: amperity-$app_name-runner" >> build/template.yaml
echo "    SemanticVersion: ${version}" >> build/template.yaml
cat util/sam/function.yaml >> build/template.yaml

echo "Building artifacts for ${filename} to upload to servless repo"

echo "Installing dependencies"
pip install requests -t build/

echo "Copying lambda runner"
mkdir build/lambdas
# NOTE this might not work with how SAM uploads files
cp src/lambdas/amperity_runner.py build/lambdas/
cp src/lambdas/helpers.py build/lambdas/
cp "src/lambdas/lambda_handlers/$filename" build/app.py

cp README.md build/README.md
cp LICENSE.txt build/LICENSE.txt

echo "Uploading artifacts to s3://amperity-serverless-repo/$app_name"

cd build/

# NOTE - going to have to figure out how to pass in version
sam package --template template.yaml --output-template-file packaged.yaml --s3-bucket amperity-lambda-app --s3-prefix $app_name

echo "\n--------------------\n\n"
echo "Finished building the serverless repo package. Please double check build/packaged.yaml."
echo "If you need to bump the version number now is the time to do it."
echo "Once you are confident the app is ready to go run: \n make sam-publish region=us-west-2"
echo "\n\n--------------------\n"
