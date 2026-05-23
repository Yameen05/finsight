"""CLI: python -m app.scripts.pinecone_init"""

from app.services.vectorstore import init_index_sync


def main() -> None:
    name = init_index_sync()
    print(f"Pinecone index ready: {name}")


if __name__ == "__main__":
    main()
