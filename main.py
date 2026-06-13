import streamlit as st
import googleapiclient.discovery
import googleapiclient.errors
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import pandas as pd

# 한글 폰트 설정 (스트림릿 클라우드 환경 고려 Linux 기본 폰트 사용)
# 만약 로컬(Windows)에서 실행 시 'malgun.ttf' 등으로 변경 가능
import os
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" # 기본 폴백
if os.path.exists("/usr/share/fonts/nanum/NanumGothic.ttf"):
    FONT_PATH = "/usr/share/fonts/nanum/NanumGothic.ttf"

# 1. 유튜브 영상 ID 추출 함수
def get_video_id(url):
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return video_id_match.group(1) if video_id_match else None

# 2. 유튜브 댓글 수집 함수
def get_youtube_comments(video_id, api_key, max_results=100):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    comments = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_results, 100),
            textFormat="plainText"
        )
        
        while request and len(comments) < max_results:
            response = request.execute()
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)
            
            # 다음 페이지가 있으면 계속 수집
            if "nextPageToken" in response and len(comments) < max_results:
                request = youtube.commentThreads().list_next(request, response)
            else:
                break
                
        return comments
    except googleapiclient.errors.HttpError as e:
        st.error(f"유튜브 API 오류가 발생했습니다: {e}")
        return []

# 3. 텍스트 전처리 및 단어 빈도 계산 (한글 지원)
def clean_text_and_get_words(comments):
    full_text = " ".join(comments)
    # 한글, 영문, 숫자만 남기고 제거
    cleaned_text = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', full_text)
    
    # 단어 분리 (간이 토큰화)
    words = cleaned_text.split()
    
    # 한 글자짜리 단어나 무의미한 불용어 제거 안내
    stopwords = {'그냥', '진짜', '너무', '보고', '영상이', '영상', '완전', '시청', '구독', '좋아요'}
    words = [word for word in words if len(word) > 1 and word not in stopwords]
    
    return words, cleaned_text

# --- 스트림릿 UI 시작 ---
st.set_page_config(page_title="유튜브 댓글 심층 분석기", layout="wide")

st.title("📊 유튜브 댓글 심층 분석 및 워드 클라우드")
st.markdown("유튜브 링크를 입력하면 댓글을 수집하여 핵심 키워드와 워드 클라우드를 생성합니다.")

# 사이드바 설정 (API 키 입력 및 설정)
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("YouTube API Key를 입력하세요", type="password")
max_comments = st.sidebar.slider("수집할 댓글 수", min_value=20, max_value=500, value=100, step=20)

# 메인 입력창
video_url = st.text_input("유튜브 영상 링크(URL)를 입력하세요", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 댓글 분석 시작"):
    if not api_key:
        st.warning("사이드바에 YouTube API Key를 입력해주세요.")
    elif not video_url:
        st.warning("유튜브 영상 링크를 입력해주세요.")
    else:
        video_id = get_video_id(video_url)
        
        if not video_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다. 확인 후 다시 시도해주세요.")
        else:
            with st.spinner("유튜브에서 댓글을 수집하고 분석하는 중입니다..."):
                # 댓글 수집
                comments = get_youtube_comments(video_id, api_key, max_comments)
                
                if comments:
                    st.success(f"총 {len(comments)}개의 댓글을 성공적으로 수집했습니다!")
                    
                    # 데이터 전처리
                    words, cleaned_text = clean_text_and_get_words(comments)
                    word_counts = Counter(words)
                    
                    # 레이아웃 분할 (좌측: 워드클라우드, 우측: 빈도수 차트)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("☁️ 한글 워드 클라우드")
                        if words:
                            # 워드클라우드 생성
                            # 스트림릿 클라우드는 기본적으로 한글 폰트가 없을 수 있으므로 font_path 처리가 중요합니다.
                            try:
                                wordcloud = WordCloud(
                                    font_path=FONT_PATH,
                                    background_color="white",
                                    width=800,
                                    height=600,
                                    max_words=100
                                ).generate_from_frequencies(word_counts)
                                
                                fig, ax = plt.subplots(figsize=(10, 8))
                                ax.imshow(wordcloud, interpolation="bilinear")
                                ax.axis("off")
                                st.pyplot(fig)
                            except Exception as e:
                                st.error("워드클라우드 생성 중 폰트 오류가 발생했습니다. 아래 빈도수 차트를 참고해주세요.")
                                st.info("팁: 스트림릿 클라우드 배포 시 'packages.txt'에 나눔 폰트를 추가해야 한글이 깨지지 않습니다.")
                        else:
                            st.info("분석할 만한 유의미한 단어가 없습니다.")
                            
                    with col2:
                        st.subheader("📈 주요 키워드 Top 15")
                        if word_counts:
                            most_common = word_counts.most_common(15)
                            df_counts = pd.DataFrame(most_common, columns=['단어', '빈도수'])
                            
                            # 스트림릿 내장 차트로 시각화
                            st.bar_chart(df_counts.set_index('단어'))
                            st.dataframe(df_counts, use_container_width=True)
                        else:
                            st.info("데이터가 부족합니다.")
                    
                    # 댓글 원본 보기
                    with st.expander("💬 수집된 원본 댓글 보기"):
                        for i, c in enumerate(comments, 1):
                            st.write(f"**{i}.** {c}")
                            st.markdown("---")
                else:
                    st.info("수집된 댓글이 없거나 영상의 댓글 기능이 꺼져있을 수 있습니다.")
