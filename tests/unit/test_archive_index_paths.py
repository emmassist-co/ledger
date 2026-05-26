from __future__ import annotations

from pathlib import Path

from ledger.archive_index.paths import ArchiveCorpusPaths, ArchiveIndexPaths


def test_archive_index_paths_expose_dr_and_dar_corpora(tmp_path: Path) -> None:
    paths = ArchiveIndexPaths(tmp_path / "archive-index")

    assert paths.root == tmp_path / "archive-index"
    assert paths.artifacts_root == paths.root / "artifacts"
    assert paths.index_root == paths.root / "index"
    assert paths.source_root == paths.root / "source"

    assert paths.corpus("dar").artifacts_root == paths.artifacts_root / "dar"
    assert paths.corpus("dr").artifacts_root == paths.artifacts_root / "dr"


def test_dr_corpus_paths_include_expected_artifact_directories(tmp_path: Path) -> None:
    corpus = ArchiveIndexPaths(tmp_path / "archive-index").corpus("dr")

    assert isinstance(corpus, ArchiveCorpusPaths)
    assert corpus.registry_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "registry"
    assert corpus.acts_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "acts"
    assert corpus.article_blocks_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "article-blocks"
    assert corpus.consolidation_notes_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "consolidation-notes"
    assert corpus.relations_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "relations"
    assert corpus.facets_dir == tmp_path / "archive-index" / "artifacts" / "dr" / "facets"


def test_archive_paths_build_stable_artifact_file_names(tmp_path: Path) -> None:
    corpus = ArchiveIndexPaths(tmp_path / "archive-index").corpus("dr")

    registry_path = corpus.artifact_path("registry", "reg-dr-lei-13-2023")
    article_block_path = corpus.artifact_path("article_block", "art-irc-45-1")

    assert registry_path == corpus.registry_dir / "reg-dr-lei-13-2023.md"
    assert article_block_path == corpus.article_blocks_dir / "art-irc-45-1.md"
