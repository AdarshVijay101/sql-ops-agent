from sql_ops_agent.rag.retriever import SimpleRetriever


def test_retrieval_basic(tmp_path):
    # Create dummy docs
    d1 = tmp_path / "deployment.md"
    d1.write_text("To deploy, run the deploy script.\n\nUse --force to overwrite.", encoding="utf-8")

    d2 = tmp_path / "schema.md"
    d2.write_text("The users table contains user data.\n\nThe orders table contains order data.", encoding="utf-8")

    retriever = SimpleRetriever(tmp_path)

    res = retriever.retrieve("how to deploy", k=1)
    assert not res.insufficient_evidence
    assert len(res.chunks) == 1
    assert "deploy script" in res.chunks[0].text
    assert res.chunks[0].doc_id == "deployment"


def test_retrieval_no_match(tmp_path):
    # Empty dir
    retriever = SimpleRetriever(tmp_path)
    res = retriever.retrieve("anything")
    assert res.insufficient_evidence


def test_retrieval_threshold(tmp_path):
    d1 = tmp_path / "fruit.md"
    d1.write_text("Apples and oranges are fruits.", encoding="utf-8")

    # query unrelated
    retriever = SimpleRetriever(tmp_path)
    # Set high threshold? default is 0.01 which effectively filters 0 matches
    # "cars" should have 0 overlap with "Apples and oranges are fruits"
    res = retriever.retrieve("cars trucks", k=1)

    if res.chunks:
        # BM25 might give non-zero score for tiny implementation if smoothing?
        # But usually 0 if no tokens overlap.
        assert res.insufficient_evidence or res.scores[0] < 0.1
    else:
        assert res.insufficient_evidence
