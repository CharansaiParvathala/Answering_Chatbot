import streamlit as st 
import PyPDF2 as pp

import google.generativeai as gemini

import re

import yt_dlp

def clean_text(text):

    if not isinstance(text, str):

        return ""

    text = re.sub(r'\d{2}:\d{2}:\d{2}(\.\d{3})? --> \d{2}:\d{2}:\d{2}(\.\d{3})?', '', text)

    text = re.sub(r'align:start position:\d+%', '', text)

    text = re.sub(r'<[^>]*>', '', text)

    lines = text.splitlines()

    unique_lines = list(dict.fromkeys(line.strip() for line in lines if line.strip()))

    return " ".join(unique_lines)



def download_subtitles(video_url, lang='en'):

    ydl_opts = {

        'writeautomaticsub': True,

        'subtitleslangs': [lang],

        'skip_download': True,

        'subtitlesformat': 'vtt',

    }



    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            result = ydl.extract_info(video_url, download=False)

            video_id = result.get('id')



            if 'requested_subtitles' in result and lang in result['requested_subtitles']:

                ydl_opts['outtmpl'] = f"{video_id}.%(ext)s"

                with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:

                    ydl_download.download([video_url])



                subtitle_file = f"{video_id}.en.vtt"

                with open(subtitle_file, 'r', encoding='utf-8') as file:

                    raw_content = file.read()



                cleaned_text = clean_text(raw_content)

                if cleaned_text:

                    return cleaned_text

                else:

                    st.warning("No subtitles found after cleaning.")

            else:

                st.warning(f"No subtitles available in '{lang}' for this video.")

    except Exception as e:

        st.error("Please Provide Valid YouTube URL")

    return ""



def main():

    hide_st_style = """

            <style>

            #MainMenu {visibility: hidden;}

            header {visibility: hidden;}

            MainMenu {visibility: hidden}

            .reportview-container .main footer {visibility: hidden;}

            </style>

            """

    st.markdown(hide_st_style, unsafe_allow_html=True)

    emp = st.empty()

    if 'text' not in st.session_state:

        st.session_state.text = ""

    if 'history' not in st.session_state:

        st.session_state.history = []

    if 'first_time' not in st.session_state:

        st.session_state.first_time = True

    if 'radio_option' not in st.session_state:

        st.session_state.radio_option = None

    if 'vid' not in st.session_state:

        st.session_state.vid = None

    if 'pd' not in st.session_state:

        st.session_state.pd = None



    mode = st.sidebar.radio('Select Your Query Mode', ['YouTube', 'PDF'], index=0)

    if not st.session_state.radio_option == mode:

        st.session_state.first_time = True

        st.session_state.history = []

        st.session_state.radio_option = mode

    pdfile = url = None



    if mode == 'PDF':

        pdfile = st.file_uploader('Upload Your PDF', type='pdf')

        # Clear and update text when a new PDF is uploaded

        if pdfile and (st.session_state.pd != pdfile):

            st.session_state.text = ""

            st.session_state.history = []

            st.session_state.pd = pdfile

            with st.spinner('Extracting information from PDF..'):

                pdf = pp.PdfReader(pdfile)

                for page in pdf.pages:

                    st.session_state.text += page.extract_text()



    if mode == 'YouTube':

        url = st.text_input('Enter Your YouTube Video URL:')

        # Clear and update text when a new URL is entered

        if url and (st.session_state.vid != url):

            st.session_state.text = ""

            st.session_state.history = []

            st.session_state.vid = url

            with st.spinner('Extracting information from YouTube..'):

                st.session_state.text = download_subtitles(url)



    if st.session_state.text:

        gemini.configure(api_key="AIzaSyDBWGGve2AxQJ0i6qjDzX0YdDNmvrQzTxs")



        generation_config = {

            "temperature": 1,

            "top_p": 0.95,

            "top_k": 40,

            "max_output_tokens": 8192,

            "response_mime_type": "text/plain",

        }



        model = gemini.GenerativeModel(

            model_name="gemini-1.5-flash",

            generation_config=generation_config,

            system_instruction=(

                "You are a teacher who answers every question asked by the user. "

                "Use the source text to answer questions. "

                "If the answer to a question is not found in the provided text, respond using your own knowledge "

                "and clearly state that the answer is not found in the text content and is AI-generated."

                "If user type /quiz must give response based on your instruction text in this format:"

                "<q>question1<o>option1<o>option2<o>option3<o>option4<o>correct answer<q>question<o>option1<o>option2<o>option3<o>option4<o>correct answer"

                "Example:<q>which one is eatable<o>cycle<o>car<o>carrot<o>sand<o>carrot dont add any extra other than this for quiz"

                "give me response exactly like this in specified format remember every responce to quiz must start with <q>"

                f"source text : {st.session_state.text}"

            ),

        )

        st.session_state.first_time = False

        try:

            chat_session = model.start_chat(history=st.session_state.history)

            query = emp.chat_input("Ask your question:")

            if query:

                response = chat_session.send_message(query)

                st.session_state.history.append({'role': 'user', 'parts': [query]})

                st.session_state.history.append({'role': 'model', 'parts': [response.text]})



            if st.session_state.history:

                for i in range(0, len(st.session_state.history), 2):

                    user_entry = st.session_state.history[i]

                    model_entry = st.session_state.history[i + 1] if i + 1 < len(st.session_state.history) else None

                    user_message = user_entry.get('parts', ['No message'])[0]

                    with st.chat_message('user'):

                        st.write(user_message)

                    if model_entry:

                        qna = []

                        model_message = model_entry.get('parts', ['No message'])[0]



                        if model_message.startswith('<q>'):

                            quiz = model_message.split('<q>')

                            qna = [q.split("<o>") for q in quiz if q.strip()]

                            with st.chat_message('assistant'):

                                with st.expander("SMART QUIZ"):

                                    for q in qna:

                                        q = [item.strip() for item in q if item.strip()]



                                        if len(q) == 6:

                                            question_text = q[0]

                                            options = ["Select an option"] + q[1:5]

                                            correct_answer = q[5]



                                            selected_option = st.radio(question_text, options, index=0)



                                            if selected_option != "Select an option":

                                                if selected_option == correct_answer:

                                                    st.success("Correct!")

                                                else:

                                                    st.error(f"Incorrect! The correct answer is: {correct_answer}")

                                            else:

                                                st.info("Please select an option.")

                                        else:

                                            st.warning(f"Invalid question format: {q}")

                        else:

                            with st.chat_message('assistant'):

                                st.write(model_message)



        except Exception as e:

            st.error(f"An error occurred: {str(e)}")

if __name__ == '__main__':

    main()
