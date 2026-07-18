import streamlit as st

from settings import get_secret_value


def require_login():
    app_username = get_secret_value("APP_USERNAME")
    app_password = get_secret_value("APP_PASSWORD")

    if not app_username or not app_password:
        st.warning(
            "还没有配置访问账号。请在环境变量或 Streamlit Secrets 中配置 "
            "APP_USERNAME 和 APP_PASSWORD。"
        )
        st.stop()

    st.session_state.setdefault("is_authenticated", False)
    st.session_state.setdefault("current_username", "")

    if st.session_state.is_authenticated:
        with st.sidebar:
            st.success(f"已登录：{st.session_state.current_username}")
            if st.button("退出访问"):
                st.session_state.is_authenticated = False
                st.session_state.current_username = ""
                st.rerun()
        return

    st.subheader("账号登录")
    st.caption("请输入用户名和密码后继续使用企业知识库智能助手。")

    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("访问密码", type="password")
        submitted = st.form_submit_button("进入应用", type="primary")

    if submitted:
        if username == app_username and password == app_password:
            st.session_state.is_authenticated = True
            st.session_state.current_username = username
            st.rerun()
        else:
            st.error("用户名或密码不正确，请重新输入。")

    st.stop()
