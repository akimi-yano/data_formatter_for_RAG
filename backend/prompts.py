"""
Prompts for Claude AI to convert structured data to natural language
"""

# Generic prompt for table/chart extraction to natural language
STRUCTURED_DATA_EXTRACTION_PROMPT = """あなたは、構造化データ（表、チャート、図表など）を分析し、情報を欠落させずに自然言語の構造化テキストに変換する専門家です。

以下のMarkdown形式のデータを、**情報の欠落なく**、構造化されたRAG（Retrieval Augmented Generation）用のテキストデータに変換してください。

## 処理手順

### 1. 定義フェーズ：軸と構造の定義
まず、このデータの構成要素を整理してください：

- **縦軸（行）の項目**：カテゴリ、大項目、中項目などの階層構造をすべて抽出してください
- **横軸（列）の項目**：列見出しが多段階層になっている場合、その階層をすべて明文化してください
- **凡例・記号の確認**：「○」「×」「△」「-」「✓」「✗」などの記号や、数値、テキストが何を意味するか、データ内から抽出してください
- **データ構造の特定**：表形式、リスト形式、フロー図、組織図など、どのような構造を持つデータかを明確にしてください

### 2. 抽出フェーズ：全データの逐次記述
データの各要素を以下のフォーマットで書き出してください。**データが空欄や「-」であっても省略しないでください。**

**【記述フォーマット】**
```
[行項目パス] (例: カテゴリA > サブカテゴリB > 項目C)
[列項目パス] (例: 条件1 > 条件2 > 詳細条件3)
[セル内容] (例: ○：可能 / ×：不可 / 数値 / テキスト / 空欄)
[適用される注釈] (例: 注1を適用 / 補足説明あり)
```

**重要：**
- すべてのセル（交差点）について記述してください
- 空欄やハイフン「-」も明記してください
- 複数行や複数列にまたがるセルの場合、その範囲を明記してください
- 階層構造がある場合、「>」記号で親子関係を表現してください

### 3. 統合フェーズ：注釈・補足情報の論理合成
データに関連する注釈、脚注、補足説明をすべてリストアップし、以下を明確にしてください：

- **注釈の内容**：各注釈が何を説明しているか
- **適用対象**：どの項目、どのセルに適用されるか
- **条件・例外**：特定の条件下でのみ適用される場合、その条件を明記
- **依存関係**：複数の注釈が組み合わさる場合、その関係性を説明

### 4. 要約フェーズ：自然言語による全体解説
上記のデータに基づき、人間とAIが理解しやすい文章で全体を解説してください：

- **データの概要**：このデータが何を表しているか
- **主要なルール・パターン**：データから読み取れる主要な規則や傾向
- **例外条件**：特殊なケース、例外的な条件がある場合は強調
- **重要な制約**：特定の条件下でのみ有効な情報がある場合は明記
- **関連性・依存関係**：項目間の関連性や依存関係

**出力形式：**
- 箇条書き形式で出力してください（まとめずに、詳細を保持）
- RAGシステムで検索しやすいよう、キーワードを明確に含めてください
- 曖昧な表現を避け、具体的に記述してください

### 5. 検証フェーズ：精度確認
回答を出力する前に、以下を**3回**再確認してください：

1. **座標の確認**：縦軸の項目名と横軸の項目名が正確か
2. **記号の確認**：記号やマーカー（○、×など）が元データと一致しているか
3. **注釈の確認**：注釈の適用対象と内容が正確か

もし矛盾や誤りを発見した場合は、修正してから出力してください。

---

## 入力データ

以下のMarkdownデータを処理してください：

{markdown_content}

---

## 出力

上記の手順に従って、構造化されたRAG用のテキストデータを出力してください。"""


# Simplified prompt for non-tabular data
GENERAL_EXTRACTION_PROMPT = """以下のMarkdown形式のデータを、RAG（Retrieval Augmented Generation）システムで活用しやすい、構造化された自然言語テキストに変換してください。

## 要件

1. **情報の完全性**：元データの情報を欠落させずに変換してください
2. **構造の保持**：階層構造、リスト、セクションなどの構造を明確に保ってください
3. **検索可能性**：重要なキーワードを明確に含め、検索しやすい形式にしてください
4. **明確性**：曖昧な表現を避け、具体的に記述してください
5. **箇条書き形式**：まとめすぎず、詳細を箇条書きで保持してください

## 処理手順

1. **データの分類**：このデータが何を表しているか（文書、説明、手順、規則など）を明確にする
2. **主要な情報の抽出**：重要なポイント、ルール、手順、定義などを抽出する
3. **詳細の展開**：各項目について、詳細情報を漏らさず記述する
4. **関連性の明記**：項目間の関連性や依存関係があれば明記する
5. **補足情報の統合**：注釈、例外、条件などを適切に統合する

---

## 入力データ

{markdown_content}

---

## 出力

上記の要件と手順に従って、RAG用の構造化テキストを出力してください。"""


def get_prompt_for_data(markdown_content: str, use_table_prompt: bool = None) -> str:
    """
    Get appropriate prompt based on data type
    
    Args:
        markdown_content: The markdown content to process
        use_table_prompt: If True, use table-specific prompt. If False, use general prompt.
                         If None, automatically detect based on content.
    
    Returns:
        Formatted prompt string
    """
    if use_table_prompt is None:
        # Auto-detect if content contains table-like structures
        table_indicators = [
            "|", "---", "<table>", "<tr>", "<td>", 
            "縦軸", "横軸", "行", "列", "セル"
        ]
        use_table_prompt = any(indicator in markdown_content for indicator in table_indicators)
    
    if use_table_prompt:
        return STRUCTURED_DATA_EXTRACTION_PROMPT.format(markdown_content=markdown_content)
    else:
        return GENERAL_EXTRACTION_PROMPT.format(markdown_content=markdown_content)


# Custom prompt template for specific use cases
CUSTOM_PROMPT_TEMPLATE = """あなたは構造化データを自然言語に変換する専門家です。

## タスク
{task_description}

## 要件
{requirements}

## 入力データ
{markdown_content}

## 出力
上記の要件に従って処理してください。"""


def create_custom_prompt(markdown_content: str, task_description: str, requirements: str) -> str:
    """
    Create a custom prompt for specific use cases
    
    Args:
        markdown_content: The markdown content to process
        task_description: Description of the specific task
        requirements: Specific requirements for the output
    
    Returns:
        Formatted custom prompt
    """
    return CUSTOM_PROMPT_TEMPLATE.format(
        task_description=task_description,
        requirements=requirements,
        markdown_content=markdown_content
    )
