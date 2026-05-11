package com.example.backend.dto;

import com.example.backend.entity.Font;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
public class FontListResponse {

    private final String fontId;
    private final String fontName;
    private final String type;
    private final LocalDateTime createdAt;

    public FontListResponse(Font font) {
        this.fontId = font.getFontId();
        this.fontName = font.getFontName();
        this.type = font.getType().name();
        this.createdAt = font.getCreatedAt();
    }
}
