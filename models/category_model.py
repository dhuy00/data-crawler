"""
Pydantic models for data validation.

Defines schema for categories, products, and comments.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class CategoryModel(BaseModel):
    """Category model for hierarchy data."""
    
    lv1_name: str = Field(..., description="Level 1 category name")
    lv1_url: str = Field(..., description="Level 1 category URL")
    lv2_name: Optional[str] = Field(None, description="Level 2 category name")
    lv2_url: Optional[str] = Field(None, description="Level 2 category URL")
    lv3_name: Optional[str] = Field(None, description="Level 3 category name")
    lv3_url: Optional[str] = Field(None, description="Level 3 category URL")
    category_id: Optional[str] = Field(None, description="Extracted category ID")
    category_url: Optional[str] = Field(None, description="Active category URL")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "lv1_name": "Điện thoại",
                "lv1_url": "https://tiki.vn/c123",
                "lv2_name": "iPhone",
                "lv2_url": "https://tiki.vn/c124",
                "lv3_name": "iPhone 15",
                "lv3_url": "https://tiki.vn/c125",
                "category_id": "125",
                "category_url": "https://tiki.vn/c125",
            }
        }


class ProductModel(BaseModel):
    """Product model for e-commerce items."""
    
    # Category information
    lv1_name: Optional[str] = Field(None, description="Level 1 category")
    lv1_url: Optional[str] = Field(None)
    lv2_name: Optional[str] = Field(None, description="Level 2 category")
    lv2_url: Optional[str] = Field(None)
    lv3_name: Optional[str] = Field(None, description="Level 3 category")
    lv3_url: Optional[str] = Field(None)
    category_id: str = Field(..., description="Category ID")
    category_url: Optional[str] = Field(None)
    
    # Pagination metadata
    page: int = Field(..., description="Page number in listing")
    position: int = Field(..., description="Position in page")
    
    # Core product information
    product_id: str = Field(..., description="Unique product ID")
    seller_product_id: Optional[str] = Field(None, description="Seller-specific product ID")
    sku: Optional[str] = Field(None, description="Stock Keeping Unit")
    product_name: str = Field(..., description="Product name")
    product_url: Optional[str] = Field(None, description="Product detail page URL")
    brand_name: Optional[str] = Field(None, description="Brand name")
    
    # Pricing
    price: Optional[float] = Field(None, description="Current selling price")
    list_price: Optional[float] = Field(None, description="List price")
    original_price: Optional[float] = Field(None, description="Original price")
    discount: Optional[float] = Field(None, description="Discount amount")
    discount_rate: Optional[float] = Field(None, description="Discount percentage")
    
    # Ratings and reviews
    rating_average: Optional[float] = Field(None, description="Average rating (0-5)")
    review_count: int = Field(default=0, description="Number of reviews")
    
    # Sales information
    quantity_sold_text: Optional[str] = Field(None, description="Formatted quantity sold")
    quantity_sold_value: Optional[int] = Field(None, description="Numeric quantity sold")
    
    # Media
    thumbnail_url: Optional[str] = Field(None, description="Product thumbnail URL")
    
    @validator("rating_average")
    def validate_rating(cls, v):
        if v is not None and not (0 <= v <= 5):
            raise ValueError("Rating must be between 0 and 5")
        return v
    
    @validator("seller_product_id", pre=True)
    def normalize_seller_product_id(cls, v):
        if v is None:
            return v
        return str(v)

    @validator("price", "discount", pre=True)
    def convert_price(cls, v):
        if isinstance(v, str):
            return float(v.replace(",", "")) if v else None
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "category_id": "1234",
                "page": 1,
                "position": 1,
                "product_id": "567890",
                "product_name": "iPhone 15 Pro",
                "brand_name": "Apple",
                "price": 25000000,
                "rating_average": 4.8,
                "review_count": 1500,
                "quantity_sold_value": 5000,
            }
        }


class CommentModel(BaseModel):
    """Comment/Review model for product feedback."""
    
    # Product reference
    product_id: str = Field(..., description="Product ID")
    seller_product_id: Optional[str] = Field(None)
    product_name: Optional[str] = Field(None)
    product_url: Optional[str] = Field(None)
    
    # Category reference
    category_id: Optional[str] = Field(None)
    category_url: Optional[str] = Field(None)
    lv1_name: Optional[str] = Field(None)
    lv2_name: Optional[str] = Field(None)
    lv3_name: Optional[str] = Field(None)
    
    # Product context
    product_review_count: int = Field(default=0)
    product_rating_average: Optional[float] = Field(None)
    
    # Pagination metadata
    comment_page: int = Field(..., description="Page number")
    comment_position: int = Field(..., description="Position in page")
    
    # Comment core information
    comment_id: str = Field(..., description="Unique comment ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    customer_name: Optional[str] = Field(None, description="Customer username")
    customer_full_name: Optional[str] = Field(None, description="Customer full name")
    customer_region: Optional[str] = Field(None, description="Customer region")
    customer_avatar_url: Optional[str] = Field(None)
    
    # Comment content
    rating: Optional[int] = Field(None, description="Star rating (1-5)")
    title: Optional[str] = Field(None, description="Review title")
    content: Optional[str] = Field(None, description="Review content")
    
    # Comment metadata
    thank_count: int = Field(default=0, description="Number of thanks")
    score: Optional[float] = Field(None, description="Review score")
    status: Optional[str] = Field(None, description="Review status")
    is_photo: bool = Field(default=False, description="Has photos")
    
    # Seller information
    seller_id: Optional[str] = Field(None)
    seller_name: Optional[str] = Field(None)
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    created_at_text: Optional[str] = Field(None, description="Formatted creation date")
    purchased_at: Optional[str] = Field(None, description="Purchase date")
    
    @validator("rating")
    def validate_rating(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v

    @validator("product_id", "seller_product_id", "comment_id", "customer_id", "seller_id", pre=True)
    def normalize_string_ids(cls, v):
        if v is None:
            return v
        return str(v)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "product_id": "567890",
                "product_name": "iPhone 15 Pro",
                "comment_id": "comment123",
                "customer_name": "customer_xyz",
                "rating": 5,
                "title": "Great phone!",
                "content": "Very satisfied with this product",
                "thank_count": 10,
                "created_at": "2024-01-15T10:30:00",
            }
        }
