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

    @Column(nullable = false)
    private LocalDateTime createdAt;

    public Font(User user, String fontName, String fontId, String ttfPath) {
        this.user = user;
        this.fontName = fontName;
        this.fontId = fontId;
        this.ttfPath = ttfPath;
        this.createdAt = LocalDateTime.now();
    }
}