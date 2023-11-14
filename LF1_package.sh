pip3 install --target ./package requests-aws4auth opensearch-py requests

cd package
zip -r ../deployment-LF1.zip .

cd ..
zip deployment-LF1.zip LF1-HW2.py