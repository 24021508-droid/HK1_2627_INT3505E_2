$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
newman run books-api.postman_collection.json `
  -e postman/local.postman_environment.json `
  -r "cli,junit" `
  --reporter-junit-export reports/junit.xml

