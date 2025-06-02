import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import math
from typing import Dict, List, Tuple, Set
import re
from urllib.parse import quote, urljoin
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class WebConceptScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search_wikipedia(self, word: str, max_concepts: int = 10) -> List[str]:
        """Wikipedia検索から関連概念を取得"""
        concepts = []
        try:
            # Wikipedia検索API
            search_url = f"https://ja.wikipedia.org/api/rest_v1/page/summary/{quote(word)}"
            response = self.session.get(search_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                extract = data.get('extract', '')

                # テキストから名詞を抽出（簡易版）
                concepts.extend(self._extract_concepts_from_text(extract, max_concepts // 2))

            # Wikipedia検索結果から関連ページを取得
            search_api_url = f"https://ja.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': word,
                'srlimit': 5
            }

            response = self.session.get(search_api_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                search_results = data.get('query', {}).get('search', [])

                for result in search_results[:3]:
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    concepts.extend(self._extract_concepts_from_text(f"{title} {snippet}", 3))

        except Exception as e:
            st.warning(f"Wikipedia検索エラー: {str(e)}")

        return list(set(concepts))[:max_concepts]

    def search_weblio(self, word: str, max_concepts: int = 8) -> List[str]:
        """Weblio辞書から関連概念を取得"""
        concepts = []
        try:
            url = f"https://www.weblio.jp/content/{quote(word)}"
            response = self.session.get(url, timeout=5)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # 意味や説明文から概念を抽出
                content_divs = soup.find_all('div', class_=['kiji', 'NetDicBody'])
                for div in content_divs[:2]:
                    text = div.get_text()
                    concepts.extend(self._extract_concepts_from_text(text, max_concepts // 2))

        except Exception as e:
            st.warning(f"Weblio検索エラー: {str(e)}")

        return list(set(concepts))[:max_concepts]

    def search_google_related(self, word: str, max_concepts: int = 8) -> List[str]:
        """Google検索の関連キーワードを取得（シミュレーション）"""
        # 実際のGoogle検索APIは有料のため、シミュレーションデータを使用
        related_patterns = {
            "技術": ["AI", "プログラミング", "イノベーション", "デジタル", "自動化", "効率", "未来", "データ"],
            "自然": ["環境", "生態系", "動物", "植物", "気候", "保護", "循環", "多様性"],
            "食べ物": ["栄養", "健康", "料理", "文化", "味", "食材", "レシピ", "食事"],
            "音楽": ["メロディー", "リズム", "楽器", "感情", "芸術", "表現", "文化", "創作"],
            "スポーツ": ["健康", "体力", "競技", "チーム", "練習", "技術", "精神", "成長"],
            "学習": ["知識", "理解", "記憶", "成長", "発見", "好奇心", "努力", "達成"],
        }

        # 部分一致で関連概念を検索
        concepts = []
        for key, values in related_patterns.items():
            if word in key or key in word:
                concepts.extend(values)

        # ランダムに追加の概念を生成
        if len(concepts) < max_concepts:
            additional = ["創造", "発想", "アイデア", "革新", "変化", "成長", "発展", "進歩"]
            concepts.extend(random.sample(additional, min(max_concepts - len(concepts), len(additional))))

        return concepts[:max_concepts]

    def _extract_concepts_from_text(self, text: str, max_concepts: int = 5) -> List[str]:
        """テキストから概念を抽出（簡易版）"""
        if not text:
            return []

        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)

        # 日本語の名詞っぽい単語を抽出（簡易版）
        # カタカナ、ひらがな、漢字の組み合わせ
        patterns = [
            r'[ァ-ヶー]{2,8}',  # カタカナ
            r'[一-龯]{2,6}',  # 漢字
            r'[ぁ-ゖ]{2,6}',  # ひらがな
        ]

        concepts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            concepts.extend(matches)

        # 不要な単語を除外
        exclude_words = {'です', 'ます', 'である', 'として', 'について', 'により', 'によって', 'から', 'まで', 'など',
                         'こと', 'もの', 'ため', 'ところ', 'とき', 'ここ', 'そこ', 'あそこ', 'これ', 'それ', 'あれ'}
        concepts = [c for c in concepts if c not in exclude_words and len(c) >= 2]

        return list(set(concepts))[:max_concepts]


class ConceptVisualizer:
    @staticmethod
    def calculate_positions(center_x: float, center_y: float, num_items: int, radius: float = 120) -> List[
        Tuple[float, float]]:
        """中心点の周りに概念を配置する座標を計算"""
        if num_items == 0:
            return []

        positions = []
        for i in range(num_items):
            angle = (2 * math.pi * i) / num_items
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions.append((x, y))
        return positions

    @staticmethod
    def create_concept_map(center_word: str, concepts: Dict[str, List[str]]) -> str:
        """動的概念マップを作成"""
        if not center_word or not concepts:
            return '<div style="text-align: center; padding: 50px;">概念を検索中...</div>'

        width, height = 800, 600
        center_x, center_y = width // 2, height // 2

        svg_content = f'''
        <div style="display: flex; justify-content: center;">
            <svg width="{width}" height="{height}" style="border: 1px solid #ddd; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 12px;">
                <!-- 中心の単語 -->
                <circle cx="{center_x}" cy="{center_y}" r="40" fill="#2E7D32" stroke="#1B5E20" stroke-width="3"/>
                <text x="{center_x}" y="{center_y + 5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="white">{center_word}</text>
        '''

        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
        source_colors = {"Wikipedia": "#FF6B6B", "Weblio": "#4ECDC4", "関連検索": "#45B7D1"}

        radius_offset = 0
        for source, concept_list in concepts.items():
            if not concept_list:
                continue

            source_radius = 150 + radius_offset
            positions = ConceptVisualizer.calculate_positions(center_x, center_y, len(concept_list), source_radius)
            color = source_colors.get(source, colors[0])

            for i, (concept, (x, y)) in enumerate(zip(concept_list, positions)):
                # 線を描画
                svg_content += f'<line x1="{center_x}" y1="{center_y}" x2="{x}" y2="{y}" stroke="#ccc" stroke-width="2" stroke-dasharray="5,5" opacity="0.7"/>'

                # 概念の円
                svg_content += f'<circle cx="{x}" cy="{y}" r="25" fill="{color}" stroke="white" stroke-width="2" opacity="0.9"/>'

                # 概念のテキスト
                display_text = concept if len(concept) <= 6 else concept[:5] + "..."
                svg_content += f'<text x="{x}" y="{y + 3}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" font-weight="bold" fill="white">{display_text}</text>'

            radius_offset += 80

        # 凡例を追加
        legend_y = 30
        for i, (source, color) in enumerate(source_colors.items()):
            legend_x = 30 + i * 120
            svg_content += f'<circle cx="{legend_x}" cy="{legend_y}" r="8" fill="{color}"/>'
            svg_content += f'<text x="{legend_x + 15}" y="{legend_y + 4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{source}</text>'

        svg_content += '</svg></div>'
        return svg_content


def initialize_session_state():
    """セッション状態を初期化"""
    if 'current_word' not in st.session_state:
        st.session_state.current_word = None
    if 'concepts' not in st.session_state:
        st.session_state.concepts = {}
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    if 'concept_dictionary' not in st.session_state:
        st.session_state.concept_dictionary = {}


def search_concepts_parallel(scraper: WebConceptScraper, word: str) -> Dict[str, List[str]]:
    """並列で複数のソースから概念を検索"""
    concepts = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        # 各検索を並列実行
        future_to_source = {
            executor.submit(scraper.search_wikipedia, word): "Wikipedia",
            executor.submit(scraper.search_weblio, word): "Weblio",
            executor.submit(scraper.search_google_related, word): "関連検索"
        }

        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                result = future.result(timeout=10)
                concepts[source] = result
            except Exception as e:
                st.warning(f"{source}の検索でエラーが発生しました: {str(e)}")
                concepts[source] = []

    return concepts


def save_concepts_to_dictionary(word: str, concepts: Dict[str, List[str]]):
    """検索した概念を辞書に保存"""
    all_concepts = []
    for concept_list in concepts.values():
        all_concepts.extend(concept_list)

    # 重複を除去
    unique_concepts = list(set(all_concepts))

    if unique_concepts:
        st.session_state.concept_dictionary[word] = unique_concepts


def export_dictionary():
    """概念辞書をJSONファイルとしてエクスポート"""
    if st.session_state.concept_dictionary:
        return json.dumps(st.session_state.concept_dictionary, ensure_ascii=False, indent=2)
    return "{}"


def main():
    st.set_page_config(
        page_title="動的概念発見アプリ",
        page_icon="🔍",
        layout="wide"
    )

    initialize_session_state()

    st.title("🔍 動的概念発見アプリ")
    st.markdown("**単語を入力すると、Webから関連概念を自動収集して発想を広げます**")

    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")

        search_sources = st.multiselect(
            "検索ソース",
            ["Wikipedia", "Weblio", "関連検索"],
            default=["Wikipedia", "Weblio", "関連検索"]
        )

        max_concepts_per_source = st.slider("ソースあたりの最大概念数", 3, 15, 8)

        st.header("📚 構築済み辞書")
        if st.session_state.concept_dictionary:
            st.write(f"登録済み単語: {len(st.session_state.concept_dictionary)}")

            # 辞書の内容を表示
            with st.expander("辞書の内容"):
                for word, concepts in list(st.session_state.concept_dictionary.items())[:5]:
                    st.write(f"**{word}**: {', '.join(concepts[:5])}...")

            # エクスポート機能
            if st.button("📥 辞書をダウンロード"):
                dictionary_json = export_dictionary()
                st.download_button(
                    label="💾 JSONファイルをダウンロード",
                    data=dictionary_json,
                    file_name="concept_dictionary.json",
                    mime="application/json"
                )
        else:
            st.info("まだ概念が登録されていません")

        # 検索履歴
        st.header("📜 検索履歴")
        if st.session_state.search_history:
            for i, word in enumerate(reversed(st.session_state.search_history[-5:])):
                if st.button(f"🔄 {word}", key=f"history_{i}"):
                    st.session_state.current_word = word
                    if word in st.session_state.concept_dictionary:
                        # 既存の概念を表示
                        concepts = st.session_state.concept_dictionary[word]
                        st.session_state.concepts = {"保存済み": concepts}
                    st.rerun()

    # メインエリア
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("📝 概念検索")

        # 検索入力
        search_word = st.text_input(
            "検索したい単語を入力:",
            placeholder="例: 人工知能、環境問題、音楽、料理..."
        )

        # 検索ボタン
        if st.button("🔍 概念を検索", type="primary"):
            if search_word and search_word.strip():
                word = search_word.strip()

                # 検索中の表示
                with st.spinner(f"「{word}」の関連概念を検索中..."):
                    scraper = WebConceptScraper()

                    # 並列検索実行
                    concepts = search_concepts_parallel(scraper, word)

                    # 選択されたソースのみフィルタ
                    filtered_concepts = {k: v for k, v in concepts.items() if k in search_sources}

                    if any(filtered_concepts.values()):
                        st.session_state.current_word = word
                        st.session_state.concepts = filtered_concepts

                        # 辞書に保存
                        save_concepts_to_dictionary(word, filtered_concepts)

                        # 履歴に追加
                        if word not in st.session_state.search_history:
                            st.session_state.search_history.append(word)

                        st.success(f"「{word}」の概念を検索しました！")
                    else:
                        st.warning("関連概念が見つかりませんでした。")
            else:
                st.error("検索する単語を入力してください。")

        # 現在の検索結果
        if st.session_state.current_word and st.session_state.concepts:
            st.subheader(f"🎯 「{st.session_state.current_word}」の関連概念")

            for source, concept_list in st.session_state.concepts.items():
                if concept_list:
                    st.write(f"**{source}** ({len(concept_list)}個):")
                    for i, concept in enumerate(concept_list, 1):
                        if st.button(f"{i}. {concept}", key=f"concept_{source}_{i}"):
                            # クリックした概念で新しい検索
                            st.session_state.current_word = concept
                            # 既存の概念があるかチェック
                            if concept in st.session_state.concept_dictionary:
                                existing_concepts = st.session_state.concept_dictionary[concept]
                                st.session_state.concepts = {"保存済み": existing_concepts}
                            else:
                                st.session_state.concepts = {}
                            st.rerun()

        # クリア機能
        if st.button("🗑️ 結果をクリア"):
            st.session_state.current_word = None
            st.session_state.concepts = {}
            st.success("検索結果をクリアしました")

    with col2:
        st.header("🎨 概念マップ")

        if st.session_state.current_word and st.session_state.concepts:
            # 概念マップを表示
            concept_map = ConceptVisualizer.create_concept_map(
                st.session_state.current_word,
                st.session_state.concepts
            )
            st.markdown(concept_map, unsafe_allow_html=True)

            # 統計情報
            st.subheader("📊 検索統計")
            total_concepts = sum(len(concepts) for concepts in st.session_state.concepts.values())

            col2_1, col2_2, col2_3 = st.columns(3)
            with col2_1:
                st.metric("中心概念", st.session_state.current_word)
            with col2_2:
                st.metric("総概念数", total_concepts)
            with col2_3:
                st.metric("検索ソース数", len([s for s in st.session_state.concepts.values() if s]))

            # 概念の詳細表示
            with st.expander("📋 概念の詳細"):
                for source, concept_list in st.session_state.concepts.items():
                    if concept_list:
                        st.write(f"**{source}**: {', '.join(concept_list)}")
        else:
            st.info("左側で単語を検索すると、ここに概念マップが表示されます。")

            # デモ用の説明
            st.subheader("🌟 アプリの特徴")
            st.markdown("""
            - **リアルタイム検索**: Webから最新の関連概念を取得
            - **複数ソース**: Wikipedia、Weblio、関連検索から情報収集
            - **視覚的表現**: 美しい概念マップで関連性を表示
            - **インタラクティブ**: 概念をクリックして連想を広げる
            - **辞書構築**: 検索した概念を自動的に辞書に蓄積
            - **履歴機能**: 過去の検索を簡単に再利用
            """)

    # フッター
    st.markdown("---")
    st.markdown("🔍 **動的概念発見**: Webから最新の情報を取得して、あなたの発想を無限に広げます")


if __name__ == "__main__":
    main()
