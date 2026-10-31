# Multi-stage Dockerfile for Spring Boot Java 21 KubeHeal Operator
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app
COPY gradlew .
COPY gradle gradle
COPY build.gradle settings.gradle ./
COPY src src

RUN chmod +x gradlew && ./gradlew bootJar --no-daemon

# Final runtime image
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

RUN addgroup -S kubeheal && adduser -S kubeheal -G kubeheal
USER kubeheal

COPY --from=builder /app/build/libs/kubeheal-1.0.0.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
