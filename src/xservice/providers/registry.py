from dataclasses import dataclass, field
from typing import Dict, Any

DEFAULT_FEATURES = {
    'rweb_video_screen_enabled': False,
    'profile_label_improvements_pcf_label_in_post_enabled': True,
    'responsive_web_profile_redirect_enabled': False,
    'rweb_tipjar_consumption_enabled': False,
    'verified_phone_label_enabled': False,
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'premium_content_api_read_enabled': False,
    'communities_web_enable_tweet_community_results_fetch': True,
    'c9s_tweet_anatomy_moderator_badge_enabled': True,
    'responsive_web_grok_analyze_button_fetch_trends_enabled': False,
    'responsive_web_grok_analyze_post_followups_enabled': True,
    'responsive_web_jetfuel_frame': True,
    'responsive_web_grok_share_attachment_enabled': True,
    'responsive_web_grok_annotations_enabled': True,
    'articles_preview_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': True,
    'tweet_awards_web_tipping_enabled': False,
    'responsive_web_grok_show_grok_translated_post': False,
    'responsive_web_grok_analysis_button_from_backend': True,
    'post_ctas_fetch_enabled': True,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'responsive_web_grok_image_annotation_enabled': True,
    'responsive_web_grok_imagine_annotation_enabled': True,
    'responsive_web_grok_community_note_auto_translation_is_enabled': False,
    'responsive_web_enhance_cards_enabled': False,
    'responsive_web_twitter_article_notes_tab_enabled': True,
    'hidden_profile_subscriptions_enabled': True,
    'subscriptions_feature_can_gift_premium': True,
    'highlights_tweets_tab_ui_enabled': True,
    'subscriptions_verification_info_verified_since_enabled': True,
    'subscriptions_verification_info_is_identity_verified_enabled': True,
    'creator_subscriptions_quote_tweet_preview_enabled': True,
    'responsive_web_text_conversations_enabled': False,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'interactive_text_enabled': True,
    'responsive_web_twitter_blue_verified_badge_is_enabled': True,
    'vibe_api_enabled': True,
    'tweetypie_unmention_optimization_enabled': True,
    'longform_notetweets_richtext_consumption_enabled': True,
}

DEFAULT_FIELD_TOGGLES = {
    'withPayments': True,
    'withAuxiliaryUserLabels': True,
    'withArticleRichContentState': True,
    'withArticlePlainText': True,
    'withGrokAnalyze': True,
    'withDisallowedReplyControls': True,
}

@dataclass
class GraphqlQuery:
    query_id: str
    method: str = "GET"
    use_transaction_id: bool = False
    features: Dict[str, Any] = field(default_factory=lambda: DEFAULT_FEATURES.copy())
    field_toggles: Dict[str, Any] = field(default_factory=lambda: DEFAULT_FIELD_TOGGLES.copy())

# Special configuration for SearchTimeline
search_timeline_features = DEFAULT_FEATURES.copy()
search_timeline_features.update({
    'content_disclosure_indicator_enabled': True,
    'content_disclosure_ai_generated_indicator_enabled': True,
})

search_timeline_field_toggles = DEFAULT_FIELD_TOGGLES.copy()
search_timeline_field_toggles.update({
    'withArticleSummaryText': True,
    'withArticleVoiceOver': True,
})

GRAPHQL_OPERATIONS = {
    "SearchTimeline": GraphqlQuery(
        query_id="n0vzau71jvBmSJzo48XTEA",
        method="POST",
        features=search_timeline_features,
        field_toggles=search_timeline_field_toggles,
    ),
    "UserByScreenName": GraphqlQuery(query_id="AWbeRIdkLtqTRN7yL_H8yw"),
    "UserByRestId": GraphqlQuery(query_id="pBP53RhZiQHExruxf-I8ig"),
    "UserTweets": GraphqlQuery(query_id="eApPT8jppbYXlweF_ByTyA"),
    "Following": GraphqlQuery(query_id="y8rK2apaUhS7Y8KF-U9w4Q", use_transaction_id=True),
    "Followers": GraphqlQuery(query_id="uTBZ2DQt9_tqwVDaEeVSog", use_transaction_id=True),
    "Likes": GraphqlQuery(query_id="JPxbOQGc_tXQ0Y29mvHKSw"),
    "UserMedia": GraphqlQuery(query_id="SJpoWbz8n_i3vN3sOPfXvw"),
    "UserTweetsAndReplies": GraphqlQuery(query_id="aDl2OEiH_EFH10mA_ewZ9A"),
    "TweetDetail": GraphqlQuery(query_id="ooUbmy0T2DmvwfjgARktiQ"),
    "Retweeters": GraphqlQuery(query_id="0BoJlKAxoNPQUHRftlwZ2w"),
    "Favoriters": GraphqlQuery(query_id="XRRjv1-uj1HZn3o324etOQ"),
}
