import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os
import re

from collections import Counter
from googleapiclient.discovery import build
from wordcloud import WordCloud
from konlpy.tag import Okt

# ------------------------
# 페이지 설정
# ------------------------

st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 유튜브 댓글 심층 분석기")

# ------------------------
# 한글 폰트 자동 다운로드
# ------------------------

FONT_FILE = "NanumGothic.ttf"

def download_font():
    if not os.path.exists(FONT_FILE):

        url = (
            "https://github.com/naver/"
            "nanumfont/releases/download/VER2.5/"
            "NanumGothic.ttf"
        )

        r = requests.get(url, timeout=30)

        with open(FONT_FILE, "wb") as f:
            f.write(r.content)

download_font()

# ------------------------
# 영상 ID 추출
# ------------------------

def extract_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None

# ------------------------
# 댓글 수집
# ------------------------

def get_comments(video_id, api_key):

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key
    )

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < 500:

        response = request.execute()

        for item in response["items"]:

            text = item["snippet"] \
                      ["topLevelComment"] \
                      ["snippet"] \
                      ["textDisplay"]

            comments.append(text)

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return comments

# ------------------------
# 형태소 분석
# ------------------------

def analyze_keywords(comments):

    okt = Okt()

    nouns = []

    for comment in comments:

        comment = re.sub(
            r"[^가-힣a-zA-Z ]",
            " ",
            comment
        )

        nouns.extend(okt.nouns(comment))

    nouns = [
        word
        for word in nouns
        if len(word) >= 2
    ]

    return Counter(nouns)

# ------------------------
# 워드클라우드
# ------------------------

def create_wordcloud(counter):

    wc = WordCloud(
        font_path=FONT_FILE,
        width=1400,
        height=700,
        background_color="white"
    )

    return wc.generate_from_frequencies(counter)

# ------------------------
# 입력창
# ------------------------

api_key = st.text_input(
    "YouTube API Key",
    type="password"
)

video_url = st.text_input(
    "유튜브 링크"
)

# ------------------------
# 실행
# ------------------------

if st.button("🚀 분석 시작"):

    if not api_key:
        st.error("API KEY를 입력하세요.")
        st.stop()

    if not video_url:
        st.error("유튜브 링크를 입력하세요.")
        st.stop()

    try:

        video_id = extract_video_id(video_url)

        if not video_id:
            st.error("올바른 유튜브 링크가 아닙니다.")
            st.stop()

        with st.spinner("댓글 수집 중..."):

            comments = get_comments(
                video_id,
                api_key
            )

        st.success(
            f"{len(comments)}개의 댓글 수집 완료"
        )

        df = pd.DataFrame({
            "댓글": comments
        })

        st.subheader("💬 댓글 데이터")

        st.dataframe(
            df,
            use_container_width=True
        )

        # 키워드 분석

        counter = analyze_keywords(comments)

        top_words = pd.DataFrame(
            counter.most_common(30),
            columns=["단어", "빈도"]
        )

        st.subheader("🔥 TOP 30 키워드")

        st.dataframe(
            top_words,
            use_container_width=True
        )

        # 워드클라우드

        st.subheader("☁️ 한글 워드클라우드")

        wc = create_wordcloud(counter)

        fig, ax = plt.subplots(
            figsize=(14, 7)
        )

        ax.imshow(wc)

        ax.axis("off")

        st.pyplot(fig)

        # 막대 그래프

        st.subheader("📈 키워드 빈도")

        fig2, ax2 = plt.subplots(
            figsize=(12, 6)
        )

        ax2.bar(
            top_words["단어"],
            top_words["빈도"]
        )

        plt.xticks(rotation=45)

        st.pyplot(fig2)

    except Exception as e:
        st.error(str(e))
