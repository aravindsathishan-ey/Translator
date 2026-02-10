import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.document import DocumentTranslationClient
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_account_sas, ResourceTypes, AccountSasPermissions

load_dotenv()

ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
SRC_CONTAINER = os.getenv("AZURE_SOURCE_CONTAINER", "transtest")
DST_CONTAINER = os.getenv("AZURE_TARGET_CONTAINER", "transtesttarget")
ENDPOINT = os.getenv("AZURE_DOCUMENT_TRANSLATION_ENDPOINT")
KEY = os.getenv("AZURE_DOCUMENT_TRANSLATION_KEY")


class Translator:
    def __init__(self):
        self.sas_token = self.generate_sas()
        self.blob_service = BlobServiceClient(f"https://{ACCOUNT_NAME}.blob.core.windows.net", credential=ACCOUNT_KEY)
        self.src_client = self.blob_service.get_container_client(SRC_CONTAINER)
        self.dst_client = self.blob_service.get_container_client(DST_CONTAINER)
        self.SOURCE_URL = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{SRC_CONTAINER}?{self.sas_token}"
        self.TARGET_URL = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{DST_CONTAINER}?{self.sas_token}"
        self.translator = DocumentTranslationClient(ENDPOINT, AzureKeyCredential(KEY))

    #generate ac levl sas token
    def generate_sas(self):
        try:
            start = datetime.now(timezone.utc) - timedelta(minutes=5)
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)

            return generate_account_sas(
                account_name=ACCOUNT_NAME,
                account_key=ACCOUNT_KEY,
                resource_types=ResourceTypes(object=True, container=True, service=True),
                permission=AccountSasPermissions(
                    read=True, write=True, list=True, delete=True, create=True
                ),
                start=start,
                expiry=expiry,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate SAS token: {e}")

    def upload_files(self, files):
        uploaded_blob_names = []
        for f in files:
            try:
                blob_name = f"{uuid.uuid4()}-{f.name}"
                blob_client = self.src_client.get_blob_client(blob_name)

                blob_client.upload_blob(
                    f,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=f.type)
                )
                uploaded_blob_names.append(blob_name)

            except Exception as e:
                st.error(f"Upload failed for {f.name}: {e}")

        return uploaded_blob_names

    def translate(self, target_language="en"):
        try:
            return self.translator.begin_translation(
                self.SOURCE_URL,
                self.TARGET_URL,
                target_language
            )
        except Exception as e:
            raise RuntimeError(f"Translation failed: {e}")

    def download_translated(self):
        translated_files = []
        for blob in self.dst_client.list_blobs():
            file_bytes = self.dst_client.get_blob_client(blob.name).download_blob().readall()
            translated_files.append((blob.name, file_bytes))
        return translated_files

    #blob lvl cleanup
    def cleanup(self, uploaded):
        #src
        for name in uploaded:
            try:
                self.src_client.delete_blob(name)
            except Exception:
                pass

        #dst
        for blob in self.dst_client.list_blobs():
            try:
                self.dst_client.delete_blob(blob.name)
            except Exception:
                pass


client = Translator()



# --- LOGOS ---

st.set_page_config(
    page_title="Doc-Translator",
    page_icon="🌐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    /* Main app background */
    .stApp {
        background-color: #000000;
    }

    /* Top header bar */
    header[data-testid="stHeader"] {
        background-color: #000000;
    }

    /* Toolbar (menu dots area) */
    div[data-testid="stToolbar"] {
        background-color: #000000;
    }

    /* Optional: remove header bottom border */
    header[data-testid="stHeader"]::after {
        background: none;
    }

    /* Text color safety */
    body {
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)




LOGO_URL = "https://th.bing.com/th/id/OIP.Wgr313SqtaL6NaKsDJfihQAAAA?o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3"
# One centered row
left, mid, right = st.columns([1, 3, 1])
with mid:
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: flex-end;
            gap: 16px;
            margin-bottom: 24px;
        ">
            <img src="{LOGO_URL}" style="height:72px;">
            <h1 style="
                margin: 0;
                padding: 0;
                font-size: 42px;
                font-weight: 600;
                line-height: 1;
                color: white;
            ">
                Doc-Translator
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    # c_logo, c_title = st.columns([1, 4])
    #
    # with c_logo:
    #     st.markdown(
    #         """
    #         <div style="
    #             height: 88px;
    #             display: flex;
    #             align-items: flex-end;
    #         ">
    #             <img src="https://th.bing.com/th/id/OIP.Wgr313SqtaL6NaKsDJfihQAAAA?o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3" width="88">
    #         </div>
    #         """,
    #         unsafe_allow_html=True
    #     )
    #
    # with c_title:
    #     st.markdown(
    #         """
    #         <div style="
    #             height: 88px;
    #             display: flex;
    #             align-items: flex-end;
    #         ">
    #             <h1 style="margin:0;">Doc-Translator</h1>
    #         </div>
    #         """,
    #         unsafe_allow_html=True
    #     )




# uploaded_files = st.file_uploader(
#     "Upload files",
#     type=["pdf", "docx", "txt", "html", "xlsx"],
#     accept_multiple_files=True
# )
#
# target_language = st.text_input("Target language (ISO code)", value="en")
#
# if st.button("Translate") and uploaded_files:
#     with st.spinner("Uploading files..."):
#         uploaded_names = client.upload_files(uploaded_files)
#
#     st.success(f"Uploaded {len(uploaded_names)} file(s).")
#     st.info("Starting translation...")
#
#     poller = client.translate(target_language)
#
#     with st.spinner("Translating..."):
#         poller.result()
#
#     st.success("Translation completed!")
#
#     st.write(f"Documents succeeded: {poller.details.documents_succeeded_count}")
#     st.write(f"Documents failed: {poller.details.documents_failed_count}")
#
#     translated = client.download_translated()
#
#     st.subheader("Download Translated Files")
#     for fname, data in translated:
#         st.download_button(f"Download {fname}", data, file_name=fname)
#
#     client.cleanup(uploaded_names)
#     st.warning("Temporary files removed.")


if "translated_files" not in st.session_state:
    # Will store: list[tuple[str, bytes]]
    st.session_state.translated_files = []
if "translate_stats" not in st.session_state:
    # Will store success/fail counts
    st.session_state.translate_stats = None
if "uploaded_temp_refs" not in st.session_state:
    # Keep uploaded_names for cleanup later
    st.session_state.uploaded_temp_refs = None

# --- UI controls ---
uploaded_files = st.file_uploader(
    "Upload files",
    type=["pdf", "docx", "txt", "html", "xlsx"],
    accept_multiple_files=True,
    key="uploader"  # stable key helps retain value across reruns
)

target_language = st.text_input("Target language (ISO code)", value="en")

rail_left, rail_right = st.columns([1, 1])
with rail_left:
    # -------- Buttons row inside the SAME rail --------
    # Two equal columns: left = Translate, right = Clear
    c_left, c_right = st.columns(2)

    with c_left:
        translate_clicked = st.button("Translate", key="translate_btn")
with rail_right:
    d_left, d_right = st.columns([4,1])

    with d_right:
        # This button will naturally align to the right edge of the rail
        clear_clicked = st.button("Clear", key="clear_btn")

# ---------------- EY Yellow styles ----------------
st.markdown("""
<style>
/* Make all st.button elements look like EY buttons and fill their column */
.stButton > button {
    width: 100% !important;                 /* fill column width */
    height: 44px !important;                /* consistent height */
    background-color: #FFCF00 !important;   /* EY Yellow */
    color: #000000 !important;              /* black text */
    border: 1px solid #E6B800 !important;   /* EY gold */
    border-radius: 10px !important;
    font-weight: 700 !important;
}
.stButton > button:hover {
    background-color: #FFD84D !important;   /* lighter EY yellow on hover */
    color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)

# --- Clear behavior: wipe state AND cleanup temps (once) ---
if clear_clicked:
    try:
        if st.session_state.uploaded_temp_refs:
            client.cleanup(st.session_state.uploaded_temp_refs)
    except Exception as e:
        st.info(f"Cleanup note: {e}")
    st.session_state.translated_files = []
    st.session_state.translate_stats = None
    st.session_state.uploaded_temp_refs = None
    # Also reset the uploader widget by changing its key (optional trick):
    # st.session_state.uploader = None
    st.rerun()

# --- Run translation only when pressed ---
if translate_clicked and uploaded_files:
    with st.spinner("Uploading files..."):
        uploaded_names = client.upload_files(uploaded_files)

    st.success(f"Uploaded {len(uploaded_names)} file(s).")
    st.info("Starting translation...")

    poller = client.translate(target_language)

    with st.spinner("Translating..."):
        poller.result()

    st.success("Translation completed!")

    # Save stats in state so they persist across reruns
    st.session_state.translate_stats = {
        "succeeded": getattr(poller.details, "documents_succeeded_count", None),
        "failed": getattr(poller.details, "documents_failed_count", None),
    }

    # Fetch translated payloads and persist in state
    translated = list(client.download_translated())  # ensure it's materialized
    # Each item should be (fname, bytes)
    st.session_state.translated_files = translated

    # Save uploaded temp refs for later explicit cleanup on 'Clear'
    st.session_state.uploaded_temp_refs = uploaded_names

# --- Show results if any are in session_state ---
if st.session_state.translate_stats:
    st.write(f"Documents succeeded: {st.session_state.translate_stats['succeeded']}")
    st.write(f"Documents failed: {st.session_state.translate_stats['failed']}")

if st.session_state.translated_files:
    st.subheader("Download Translated Files")
    for i, (fname, data) in enumerate(st.session_state.translated_files):
        # give every download button a unique, stable key
        st.download_button(
            label=f"Download {fname}",
            data=data,
            file_name=fname,
            key=f"dl_{i}_{fname}"
        )

    st.info("Use **Clear** to remove temporary files and reset the page.")
else:
    st.caption("No translated files yet. Upload and click **Translate**.")
