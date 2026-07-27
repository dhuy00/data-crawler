"""
Keyword pipeline: keyword -> search -> ranking -> comments

Implements strict comment validation to ensure high-quality output.
"""
from core.logger import logger
from crawlers import KeywordCrawler, CommentCrawler
from services import RankingService, ProductService, CommentService
from config.settings import settings


from typing import Optional


def keyword_pipeline(
    keywords: list,
    top_n: int = 50,
    output_dir: Optional[str] = None,
):
    """
    Execute keyword search pipeline with quality filtering.
    
    Args:
        keywords: List of keywords to search
        top_n: Number of top-ranked products to get comments for
        output_dir: Output directory for results (defaults to settings.RAW_OUTPUT_DIR)
    """
    logger.info(f"Starting keyword pipeline for keywords: {keywords}")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    try:
        # Step 1: Search for products by keywords
        logger.info("Step 1: Searching products by keywords...")
        with KeywordCrawler(max_products=settings.KEYWORD_MAX_PRODUCTS) as k_crawler:
            products = k_crawler.search_keywords(keywords)
        
        logger.info(f"Found {len(products)} products")
        
        # Step 2: Deduplicate products
        logger.info("Step 2: Deduplicating products...")
        products = ProductService.deduplicate_products(products)
        logger.info(f"After dedup: {len(products)} unique products")
        
        # Check if we have any products to process
        if not products:
            logger.warning("No products found for keywords. Pipeline cannot continue.")
            logger.info(f"Keyword pipeline completed with no results.")
            logger.info(f"  - Keywords: {keywords}")
            logger.info(f"  - Products found: 0")
            logger.info(f"  - Valid comments extracted: 0")
            return
        
        # Step 3: Rank products
        logger.info("Step 3: Ranking products...")
        ranker = RankingService()
        top_products = ranker.get_top_n(products, top_n)
        logger.info(f"Selected top {len(top_products)} products")
        
        # Step 4: Extract comments with strict validation
        logger.info("Step 4: Extracting comments with strict validation...")
        with CommentCrawler() as comment_crawler:
            comments = comment_crawler.crawl_products([p.dict() for p in top_products])
        
        logger.info(f"Crawled {len(comments)} comments")
        
        # Step 5: Validate and deduplicate comments
        logger.info("Step 5: Validating and deduplicating comments...")
        comments, skip_reasons = CommentService.validate_comments(comments)
        logger.info(f"After validation: {len(comments)} valid comments")
        
        comments = CommentService.deduplicate_comments(comments)
        logger.info(f"After dedup: {len(comments)} unique valid comments")
        
        # Step 6: Save results
        logger.info("Step 6: Saving results...")
        keyword_str = '+'.join(keywords)[:50]
        
        ProductService.save_products(
            top_products,
            target_output_dir,
            filename=f"keyword_top_{keyword_str}"
        )
        logger.info("Products saved")
        
        CommentService.save_comments(
            comments,
            target_output_dir,
            filename=f"keyword_comments_{keyword_str}"
        )
        logger.info("Comments saved")
        
        # Final report
        logger.info(f"Keyword pipeline completed successfully!")
        logger.info(f"  - Keywords: {keywords}")
        logger.info(f"  - Products found: {len(top_products)}")
        logger.info(f"  - Valid comments extracted: {len(comments)}")
    
    except Exception as e:
        logger.error(f"Error in keyword pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    keyword_pipeline(["iphone", "samsung"], top_n=20)
