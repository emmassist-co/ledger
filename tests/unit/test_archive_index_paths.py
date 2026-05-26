from __future__ import annotations

from pathlib import Path

from ledger.archive_index.paths import ArchiveCorpusPaths, ArchiveIndexPaths


def test_archive_index_paths_expose_named_corpora(tmp_path: Path) -> None:
    paths = ArchiveIndexPaths(tmp_path / "archive-index")

    assert paths.root == tmp_path / "archive-index"
    assert paths.artifacts_root == paths.root / "artifacts"
    assert paths.index_root == paths.root / "index"
    assert paths.source_root == paths.root / "source"

    assert paths.corpus("alpha").artifacts_root == paths.artifacts_root / "alpha"
    assert paths.corpus("beta").artifacts_root == paths.artifacts_root / "beta"


def test_corpus_paths_include_expected_artifact_directories(tmp_path: Path) -> None:
    corpus = ArchiveIndexPaths(tmp_path / "archive-index").corpus("beta")

    assert isinstance(corpus, ArchiveCorpusPaths)
    assert corpus.registry_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "registry"
    assert corpus.acts_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "acts"
    assert corpus.article_blocks_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "article-blocks"
    assert corpus.consolidation_notes_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "consolidation-notes"
    assert corpus.relations_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "relations"
    assert corpus.facets_dir == tmp_path / "archive-index" / "artifacts" / "beta" / "facets"


def test_archive_paths_build_stable_artifact_file_names(tmp_path: Path) -> None:
    corpus = ArchiveIndexPaths(tmp_path / "archive-index").corpus("beta")

    registry_path = corpus.artifact_path("registry", "reg-beta-2023")
    article_block_path = corpus.artifact_path("article_block", "art-beta-45-1")

    assert registry_path == corpus.registry_dir / "reg-beta-2023.md"
    assert article_block_path == corpus.article_blocks_dir / "art-beta-45-1.md"
