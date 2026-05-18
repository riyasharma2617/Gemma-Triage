import pytest


class MockTokenizer:
    """Minimal tokenizer mock — no transformers dependency needed for unit tests."""
    chat_template = "{% for m in messages %}{{ m['role'] }}: {{ m['content'] }}{% endfor %}"
    model_max_length = 512

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        parts = [f"{m['role']}: {m['content']}" for m in messages]
        if add_generation_prompt:
            parts.append("assistant:")
        return "\n".join(parts)


@pytest.fixture
def mock_tokenizer():
    return MockTokenizer()


@pytest.fixture
def perfect_predictions():
    labels = ["RED"] * 5 + ["YELLOW"] * 5 + ["GREEN"] * 5 + ["BLACK"] * 5
    return labels[:], labels[:], ["curated"] * 5 + ["generated"] * 15
