
typedef int FBOOL;
typedef uint32_t FENTITY;

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

typedef struct FVEC2_DOUBLE {
    double x;
    double y;
} FVEC2_DOUBLE;

typedef struct FVEC3_DOUBLE {
    double x;
    double y;
    double z;
} FVEC3_DOUBLE;

typedef struct FVEC4_DOUBLE {
    double x;
    double y;
    double z;
    double w;
} FVEC4_DOUBLE;

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

typedef struct _FFRUSTUM {
    FVEC4_FLOAT planes[6];
} FFRUSTUM;

typedef FVEC3_FLOAT FLINEAR_COLOR;
typedef FVEC4_FLOAT FLINEAR_COLOR_A;

typedef uint32_t FSAMPLER_PARAMS;
