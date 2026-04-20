from promptbranch import ChatGPTServiceClient


if __name__ == "__main__":
    with ChatGPTServiceClient(
        "http://localhost:8000",
        token="replace-me-if-you-set-CHATGPT_SERVICE_TOKEN",
    ) as client:
        print(client.healthz())
        answer = client.ask("Reply with one short sentence that says the service is ready.")
        print(answer)
