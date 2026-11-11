"""Streamlit AI chat: Gemini/LangGraph primary, v2 deterministic local fallback."""
import streamlit as st
from src.agent.agent_core import FoodGuardianAgent
from src.config import GOOGLE_API_KEY, GEMINI_MODEL, RAG_ENABLED
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService


def render_agent_chat_view():
    st.title('🤖 Food Guardian 智慧餐點推薦')
    st.caption('Gemini + LangGraph Tool Calling；可啟用 ChromaDB RAG。食安資訊僅供參考。')
    if 'fg_agent_messages' not in st.session_state:
        st.session_state.fg_agent_messages=[]
    with st.expander('AI 模式與測試說明', expanded=False):
        st.write(f'Gemini 模型：`{GEMINI_MODEL}`；RAG：{"已啟用（需先建立索引）" if RAG_ENABLED else "尚未啟用"}')
        st.write('示範問題：推薦今天晚餐、有哪些快到期食材、菠菜怎麼保存？')
        st.caption('使用 Gemini 需要有效 API Key 與額度；本地規則模式不需要 API。')
    options=['Gemini + LangGraph','本地規則（離線備援）']
    if not GOOGLE_API_KEY:
        st.info('目前未讀取到 GOOGLE_API_KEY；可先選擇本地規則模式。')
    mode_choice=st.radio('執行模式', options, horizontal=True, key='fg_agent_mode')
    if st.button('清除對話紀錄', key='fg_clear_chat'):
        st.session_state.fg_agent_messages=[]
        st.rerun()

    for item in st.session_state.fg_agent_messages:
        with st.chat_message(item['role']):
            st.markdown(item['content'])
            if item['role']=='assistant':
                st.caption('運作方式：'+item.get('mode','local'))
                with st.expander('工具呼叫紀錄'):
                    st.json(item.get('trace',[]))
    user_input=st.chat_input('請輸入食材或料理問題…')
    if not user_input: return
    history=list(st.session_state.fg_agent_messages)
    st.session_state.fg_agent_messages.append({'role':'user','content':user_input})
    with st.chat_message('user'): st.markdown(user_input)
    trace=[]; mode='local'
    with st.chat_message('assistant'):
        try:
            db=DatabaseManager(); db.initialize_database()
            service=InventoryService(db)
            if mode_choice==options[0]:
                if not GOOGLE_API_KEY:
                    raise ValueError('Gemini API Key 尚未設定；請先完成 .env，或選擇本地規則模式。')
                from src.agent.gemini_mode import create_gemini_agent
                agent=create_gemini_agent(service)
                with st.spinner('Gemini 正在查詢資料並執行工具…'):
                    answer=agent.process_query(user_input, history=history)
            else:
                agent=FoodGuardianAgent(inventory_service=service, api_key='')
                with st.spinner('本地規則模式查詢中…'):
                    answer=agent.process_query(user_input)
            mode,trace=agent.last_mode,agent.last_trace
            st.markdown(answer)
        except Exception as exc:
            # No quiet fallback: prevent users from believing failed Gemini calls were real tool reasoning.
            answer='本次查詢失敗，沒有自動改用其他模式。請檢查 API Key、模型權限、套件及網路。'
            st.error(answer)
            st.caption(f'錯誤類型：{type(exc).__name__}；詳細訊息（可能含環境資訊，請勿直接公開）：{str(exc)[:300]}')
        st.caption('運作方式：'+mode)
        with st.expander('工具呼叫紀錄'): st.json(trace)
    st.session_state.fg_agent_messages.append({'role':'assistant','content':answer,'mode':mode,'trace':trace})
