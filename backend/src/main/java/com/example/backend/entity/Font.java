package com.example.backend.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "fonts")
@Getter
@NoArgsConstructor
public class Font {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private String fontName;

    @Column(nullable = false, unique = true)
    private String fontId;

    @Column(nullable = false)
    private String ttfPath;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private FontType type;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    public enum FontType {
        MANUAL, AI
    }

    public Font(User user, String fontName, String fontId, String ttfPath, FontType type) {
        this.user = user;
        this.fontName = fontName;
        this.fontId = fontId;
        this.ttfPath = ttfPath;
        this.type = type;
        this.createdAt = LocalDateTime.now();
    }
}