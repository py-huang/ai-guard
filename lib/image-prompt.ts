/**
 * What the chat sends when a child shares a picture without typing anything.
 *
 * This sentence is checked by the safety gateway like any other message, so it must stay
 * harmless to the learned content model. Avoid words such as 「遮罩」「遮住」: the model has
 * learned to treat "cover / hide" wording as suspicious and blocked the earlier wording
 * 「請看這張已遮罩的圖片，幫我看看可以怎麼問。」, which showed children a refusal for a
 * perfectly ordinary picture. tests/test_content_model_quality.py reads this file and checks the
 * sentence against the real model, so a wording change that breaks it fails there.
 */
export const IMAGE_ONLY_PROMPT = "請看這張圖片，幫我看看可以怎麼問。";
