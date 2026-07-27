"""
Comment validator for strict data quality checks.

Implements validation rules to filter out garbage data and ensure
comments meet minimum quality standards.
"""
import re
from typing import Dict, Optional, Tuple, List
from core.logger import logger


class CommentValidator:
    """Validates comment data for quality and completeness."""
    
    # Configuration for validation
    MIN_CONTENT_LENGTH = 3  # Minimum characters in content
    MAX_CONTENT_LENGTH = 10000  # Maximum characters (spam check)
    MIN_TITLE_LENGTH = 3  # Minimum title length
    MAX_TITLE_LENGTH = 200  # Maximum title length
    
    # Spam patterns - text that indicates low-quality comments
    SPAM_PATTERNS = [
        r'^[\d\W]*$',  # Only numbers and special chars
        r'(http|https|www)',  # URLs (potential ads)
        r'(zalo|facebook|telegram|instagram|whatsapp|viber|skype)',  # Contact info
        r'(\+84|\+86|\+88)[0-9]{7,}',  # Phone numbers
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Emails
    ]
    
    # Seller response indicators
    SELLER_INDICATORS = [
        'seller reply',
        'phản hồi từ người bán',
        'trả lời của seller',
        'ghi chú từ nhà bán',
    ]
    
    # Required fields for a valid comment
    REQUIRED_FIELDS = [
        'id',
        'created_by',
        'rating',
    ]

    @classmethod
    def validate_raw_comment(cls, comment: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate raw comment data from API.
        
        Args:
            comment: Raw comment dictionary from API
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(comment, dict):
            return False, "Comment is not a dictionary"
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in comment or comment[field] is None:
                return False, f"Missing required field: {field}"
        
        # Validate rating
        rating = comment.get('rating')
        if rating is not None and not (isinstance(rating, (int, float)) and 1 <= rating <= 5):
            return False, f"Invalid rating value: {rating}"
        
        # Validate customer info
        created_by = comment.get('created_by', {})
        if not isinstance(created_by, dict):
            return False, "Invalid created_by structure"
        
        if not created_by.get('id'):
            return False, "Missing customer ID"
        
        return True, None

    @classmethod
    def validate_comment_content(cls, title: Optional[str], content: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate comment title and content for quality.
        
        Args:
            title: Comment title
            content: Comment content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # At least one of title or content must exist
        if not title and not content:
            return False, "Both title and content are empty"
        
        # Validate title if present
        if title:
            title_clean = str(title).strip()
            if len(title_clean) < cls.MIN_TITLE_LENGTH:
                return False, f"Title too short (< {cls.MIN_TITLE_LENGTH} chars)"
            
            if len(title_clean) > cls.MAX_TITLE_LENGTH:
                return False, f"Title too long (> {cls.MAX_TITLE_LENGTH} chars)"
            
            # Check for spam patterns
            is_spam, pattern = cls._check_spam_pattern(title_clean)
            if is_spam:
                return False, f"Title contains spam pattern: {pattern}"
        
        # Validate content if present
        if content:
            content_clean = str(content).strip()
            if len(content_clean) < cls.MIN_CONTENT_LENGTH:
                return False, f"Content too short (< {cls.MIN_CONTENT_LENGTH} chars)"
            
            if len(content_clean) > cls.MAX_CONTENT_LENGTH:
                return False, f"Content too long (> {cls.MAX_CONTENT_LENGTH} chars)"
            
            # Check for spam patterns
            is_spam, pattern = cls._check_spam_pattern(content_clean)
            if is_spam:
                return False, f"Content contains spam pattern: {pattern}"
        
        return True, None

    @classmethod
    def is_seller_response(cls, content: Optional[str], title: Optional[str]) -> bool:
        """
        Detect if comment is actually a seller response rather than customer review.
        
        Args:
            content: Comment content
            title: Comment title
            
        Returns:
            True if appears to be seller response
        """
        combined_text = f"{title or ''} {content or ''}".lower()
        
        for indicator in cls.SELLER_INDICATORS:
            if indicator.lower() in combined_text:
                return True
        
        return False

    @classmethod
    def _check_spam_pattern(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text matches any spam patterns.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_spam, matching_pattern)
        """
        for pattern in cls.SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, pattern
        
        return False, None

    @classmethod
    def sanitize_comment_text(cls, text: Optional[str]) -> Optional[str]:
        """
        Clean and sanitize comment text.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Cleaned text or None
        """
        if not text:
            return None
        
        text = str(text).strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\t\r')
        
        return text if text else None

    @classmethod
    def validate_and_clean_comment(
        cls,
        comment: Dict,
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Full validation and cleaning pipeline for a comment.
        
        Args:
            comment: Raw comment from API
            
        Returns:
            Tuple of (is_valid, error_message, cleaned_comment)
        """
        # First pass: validate raw structure
        is_valid, error_msg = cls.validate_raw_comment(comment)
        if not is_valid:
            return False, error_msg, None
        
        # Extract and clean content fields
        title = cls.sanitize_comment_text(comment.get('title'))
        content = cls.sanitize_comment_text(comment.get('content'))
        
        # Second pass: validate content
        is_valid, error_msg = cls.validate_comment_content(title, content)
        if not is_valid:
            return False, error_msg, None
        
        # Check if it's a seller response
        if cls.is_seller_response(content, title):
            logger.debug("Filtering out seller response comment")
            return False, "Seller response detected", None
        
        # Return cleaned comment
        cleaned_comment = comment.copy()
        cleaned_comment['title'] = title
        cleaned_comment['content'] = content
        
        return True, None, cleaned_comment


def get_comment_quality_report(
    total_comments: int,
    valid_comments: int,
    skipped_comments: Dict[str, int],
) -> Dict:
    """
    Generate quality report for comment extraction.
    
    Args:
        total_comments: Total comments attempted
        valid_comments: Valid comments extracted
        skipped_comments: Dictionary of skip reasons and counts
        
    Returns:
        Quality report dictionary
    """
    report = {
        'total_attempted': total_comments,
        'valid_extracted': valid_comments,
        'invalid_skipped': total_comments - valid_comments,
        'validity_rate': (valid_comments / total_comments * 100) if total_comments > 0 else 0,
        'skip_reasons': skipped_comments,
    }
    
    logger.info(f"Comment Quality Report: {valid_comments}/{total_comments} valid ({report['validity_rate']:.1f}%)")
    for reason, count in skipped_comments.items():
        if count > 0:
            logger.debug(f"  - {reason}: {count} comments")
    
    return report
