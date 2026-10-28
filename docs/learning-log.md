## Tuesday Oct 27th
1. Writing Architecture Decision Record (ADR) took the most amount of time because I had to justify why python over Typescript, Golang, Java/Scala
2. Learned the difference between streaming & ingesting vs querying active rental licenses API endpoint. 
    - We'll stream & ingest data to store in our database. This gives us full control of the data and allows us to improve performance of complex queries.
    - Data staleness isn't an issue because MPLS updates data once a week on Friday @ 2:45 AM. The data we have will always accurately reflect what MPLS has on their website.
3. .gitkeep file to get git to track empty folders.
4. pip freeze > requirements.txt after installing any packages to keep it up to date

## Question
- Writing Architecture Decision Record is still confusing.
- What's the issue with git not tracking empty folders?