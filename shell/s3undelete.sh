aws --output text s3api list-object-versions --bucket logs --prefix archive/ | grep -E "^DELETEMARKERS" | awk '{FS = "[\t]+"; print "aws s3api delete-object --bucket logs --key \42"$3"\42 --version-id "$5";"}' >> undeleteScript.sh