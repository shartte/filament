
typedef int FBOOL;

typedef struct FVEC2_FLOAT {
    float x;
    float y;
} FVEC2_FLOAT;

typedef struct FVEC3_FLOAT {
    float x;
    float y;
    float z;
} FVEC3_FLOAT;

typedef struct FVEC4_FLOAT {
    float x;
    float y;
    float z;
    float w;
} FVEC4_FLOAT;

typedef struct FMAT33_DOUBLE {
    double m[9];
} FMAT33_DOUBLE;

typedef struct FMAT33_FLOAT {
    float m[9];
} FMAT33_FLOAT;

typedef struct FMAT44_DOUBLE {
    double m[16];
} FMAT44_DOUBLE;

typedef struct FMAT44_FLOAT {
    float m[16];
} FMAT44_FLOAT;

typedef struct FQUATERNION_FLOAT {
    float m[4];
} FQUATERNION_FLOAT;

typedef FVEC3_FLOAT FLINEAR_COLOR;
typedef FVEC4_FLOAT FLINEAR_COLOR_A;

typedef uint32_t FSAMPLER_PARAMS;
