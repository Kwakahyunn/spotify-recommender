import streamlit as st
import sqlite3
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="Spotify 곡 추천 시스템", page_icon="🎵", layout="wide")

# DB 연결 함수
def get_db_connection():
    conn = sqlite3.connect('spotify.db')
    return conn

# 추천 SQL 실행 함수 (이전과 동일)
def get_recommendations(playlist_id, option, top_n=10):
    conn = get_db_connection()
    info_query = f"SELECT DISTINCT playlist_genre, playlist_subgenre FROM TRACK WHERE playlist_id = '{playlist_id}'"
    info_df = pd.read_sql_query(info_query, conn)
    user_genre = info_df['playlist_genre'].iloc[0]
    user_subgenre = info_df['playlist_subgenre'].iloc[0]
    
    if option == "1":
        sql = f"""
        WITH user_audio_profile AS (
            SELECT 
                AVG(danceability) AS avg_dance,
                AVG(energy) AS avg_energy,
                AVG(valence) AS avg_valence,
                AVG(acousticness) AS avg_acoustic
            FROM TRACK
            WHERE playlist_id = '{playlist_id}'
        ),
        target_subgenre_list AS (
            SELECT DISTINCT playlist_subgenre FROM TRACK WHERE playlist_id = '{playlist_id}'
        )
        SELECT DISTINCT
            '🎯 취향 저격' AS [추천 방식],
            t.track_name AS [곡명],
            t.track_artist AS [아티스트],
            t.playlist_genre AS [상위장르],
            t.playlist_subgenre AS [하위장르],
            t.track_popularity AS [인기도],
            ROUND(
                SQRT(
                    POWER(t.danceability - p.avg_dance, 2) + 
                    POWER(t.energy - p.avg_energy, 2) + 
                    POWER(t.valence - p.avg_valence, 2) + 
                    POWER(t.acousticness - p.avg_acoustic, 2)
                ), 4
            ) AS [오디오 거리]
        FROM TRACK t
        CROSS JOIN user_audio_profile p
        WHERE t.playlist_subgenre IN (SELECT playlist_subgenre FROM target_subgenre_list)
          AND t.track_id NOT IN (SELECT track_id FROM TRACK WHERE playlist_id = '{playlist_id}')
        ORDER BY [오디오 거리] ASC, t.track_popularity DESC
        LIMIT {top_n};
        """
    elif option == "2":
        sql = f"""
        WITH target_tracks AS (
            SELECT DISTINCT track_id FROM TRACK WHERE playlist_id = '{playlist_id}'
        ),
        playlist_similarity AS (
            SELECT 
                tp.playlist_id,
                COUNT(DISTINCT tp.track_id) AS intersection_count,
                (
                    SELECT COUNT(DISTINCT track_id) 
                    FROM TRACK 
                    WHERE playlist_id IN ('{playlist_id}', tp.playlist_id)
                ) AS union_count
            FROM TRACK tp
            WHERE tp.track_id IN (SELECT track_id FROM target_tracks)
              AND tp.playlist_id <> '{playlist_id}'
            GROUP BY tp.playlist_id
        )
        SELECT DISTINCT
            '🎧 연관 추천' AS [추천 방식],
            t.track_name AS [곡명],
            t.track_artist AS [아티스트],
            t.playlist_genre AS [상위장르],
            t.playlist_subgenre AS [하위장르],
            t.track_popularity AS [인기도],
            ROUND(CAST(ps.intersection_count AS FLOAT) / ps.union_count, 4) AS [Jaccard 점수]
        FROM TRACK t
        JOIN playlist_similarity ps ON t.playlist_id = ps.playlist_id
        WHERE t.track_id NOT IN (SELECT track_id FROM target_tracks)
        ORDER BY [Jaccard 점수] DESC, t.track_popularity DESC
        LIMIT {top_n};
        """
    elif option == "3":
        sql = f"""
        WITH target_tracks AS (
            SELECT DISTINCT track_id FROM TRACK WHERE playlist_id = '{playlist_id}'
        )
        SELECT DISTINCT
            '🔥 장르 히트곡' AS [추천 방식],
            t.track_name AS [곡명],
            t.track_artist AS [아티스트],
            t.playlist_genre AS [상위장르],
            t.playlist_subgenre AS [하위장르],
            t.track_popularity AS [인기도]
        FROM TRACK t
        WHERE t.playlist_genre = '{user_genre}'
          AND t.track_id NOT IN (SELECT track_id FROM target_tracks)
        ORDER BY 
            CASE WHEN t.playlist_subgenre = '{user_subgenre}' THEN 0 ELSE 1 END ASC,
            t.track_popularity DESC
        LIMIT {top_n};
        """
        
    result_df = pd.read_sql_query(sql, conn)
    conn.close()
    return result_df

# 메인 타이틀
st.title("🎧 Spotify 데이터베이스 기반 곡 추천 시스템")
st.markdown("사용자의 플레이리스트 분석을 바탕으로 맞춤형 추천 알고리즘 3가지를 제공합니다.")

# DB에서 플레이리스트 목록 가져오기
conn = get_db_connection()
playlist_df = pd.read_sql_query("SELECT DISTINCT playlist_id, playlist_name, playlist_genre, playlist_subgenre FROM TRACK", conn)

# 1. 플레이리스트 선택 옵션 (메인 화면)
st.subheader("⚙️ 플레이리스트 선택")
selected_playlist_name = st.selectbox(
    "테스트할 플레이리스트를 아래에서 골라주세요:", 
    playlist_df['playlist_name'].unique()
)

# 선택된 플레이리스트 정보 추출
selected_info = playlist_df[playlist_df['playlist_name'] == selected_playlist_name].iloc[0]
target_playlist_id = selected_info['playlist_id']

col1, col2, col3 = st.columns(3)
col1.metric("플레이리스트 이름", selected_info['playlist_name'])
col2.metric("대표 상위 장르", selected_info['playlist_genre'])
col3.metric("대표 하위 장르", selected_info['playlist_subgenre'])

# 2. 선택한 플레이리스트의 수록곡 전체 보기 (접었다 펴기)
st.markdown("---")
with st.expander(f"📂 '{selected_playlist_name}' 수록곡 전체 보기 (클릭하여 열기)"):
    tracks_query = f"""
        SELECT 
            track_name AS [곡명], 
            track_artist AS [아티스트], 
            track_album_name AS [앨범명],
            track_popularity AS [인기도] 
        FROM TRACK 
        WHERE playlist_id = '{target_playlist_id}' 
        ORDER BY track_popularity DESC
    """
    tracks_df = pd.read_sql_query(tracks_query, conn)
    st.dataframe(tracks_df, use_container_width=True)
    st.caption(f"이 플레이리스트에는 총 {len(tracks_df)}곡이 수록되어 있습니다.")

conn.close()

st.divider()

# 추천 기능 탭
st.subheader("🎵 추천 옵션 선택")
tab1, tab2, tab3 = st.tabs(["🎯 1. 취향 저격 (Vibe Match)", "🎧 2. 연관 추천 (Similar List)", "🔥 3. 장르 히트곡 (Genre Hits)"])

with tab1:
    st.write("**오디오 특성(12개 수치)의 평균 유클리드 거리가 가장 가까운 세부 취향곡을 추천합니다.**")
    if st.button("🎯 취향 저격 곡 추천받기", key="btn1"):
        df_res1 = get_recommendations(target_playlist_id, option="1")
        st.dataframe(df_res1, use_container_width=True)

with tab2:
    st.write("**Jaccard 유사도를 기반으로 내 플레이리스트와 겹침 밀도가 높은 연관 사용자 플레이리스트 곡을 추천합니다.**")
    if st.button("🎧 연관 곡 추천받기", key="btn2"):
        df_res2 = get_recommendations(target_playlist_id, option="2")
        st.dataframe(df_res2, use_container_width=True)

with tab3:
    st.write("**해당 하위/상위 장르 전체에서 인기도(Popularity)가 가장 높은 대표곡을 추천합니다.**")
    if st.button("🔥 장르 인기곡 추천받기", key="btn3"):
        df_res3 = get_recommendations(target_playlist_id, option="3")
        st.dataframe(df_res3, use_container_width=True)